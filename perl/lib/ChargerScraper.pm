package ChargerScraper;
use strict;
use warnings;
use Playwright;
use JSON;
use DateTime;
use File::Path qw(make_path remove_tree);
use File::Spec;

sub new {
    my ($class, %args) = @_;
    my $self = {
        url => $args{url},
        provider_name => $args{provider_name} || "Erlanger Stadtwerke",
        verbose => $args{verbose} || 0,
        status_data => {
            status => "Unknown",
            connectors => [],
            last_updated => undef,
            error => "Not started"
        },
        user_data_dir => File::Spec->tmpdir() . "/playwright_perl_" . $$ . "_" . int(rand(1000000))
    };
    return bless $self, $class;
}

sub _log {
    my ($self, $msg) = @_;
    my $ts = DateTime->now->strftime('%Y-%m-%d %H:%M:%S');
    print "[$ts] $msg\n";
}

sub scrape {
    my $self = shift;
    $self->_log("--- STARTING PERL SCRAPE (VERSION 1.2.0) ---");

    make_path($self->{user_data_dir});

    my $playwright = Playwright->new();
    my $chromium = $playwright->chromium;

    my $context = $chromium->launch_persistent_context($self->{user_data_dir}, {
        headless => 1,
        viewport => { width => 1280, height => 1200 },
        userAgent => "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    });

    my $page = $context->newPage();

    eval {
        $self->_log("Navigating to root to establish session...");
        $page->goto("https://ladeverbundplus.chargecloud.de/", { waitUntil => "load" });
        sleep(10);

        for my $cycle (1..15) {
            my $curr_url = $page->url();
            $self->_log("Cycle $cycle | URL: $curr_url");

            my $body_text = $page->evaluate("() => document.body.innerText");

            if ($curr_url =~ /\/settings/ || $body_text =~ /Anbieter wählen/) {
                $self->_log("Selecting Provider: $self->{provider_name}");
                $page->evaluate(<<'JS', $self->{provider_name});
                    (providerName) => {
                        const els = Array.from(document.querySelectorAll('*'));
                        const target = els.find(el => (el.innerText || "").includes(providerName));
                        if (target) target.click();
                    }
JS
                sleep(10);
                $self->_log("Navigating to station details...");
                $page->goto($self->{url}, { waitUntil => "load" });
                sleep(10);
                next;
            }

            # Cleanup Overlays
            $page->evaluate(<<'JS');
                () => {
                    const words = ["VERSTANDEN", "OK", "CLOSE", "AGREE"];
                    document.querySelectorAll('button, ion-button, span, div').forEach(b => {
                        if (words.includes((b.innerText || "").trim().toUpperCase())) b.click();
                    });
                    const sel = 'ion-loading, ion-backdrop, .loading-wrapper, ion-spinner, .backdrop-no-tappable, ion-modal';
                    document.querySelectorAll(sel).forEach(el => el.remove());
                    document.body.classList.remove('modal-open');
                }
JS

            # Extraction
            my $extraction = $page->evaluate(<<'JS');
                () => {
                    const nodes = [];
                    const idRegex = /DE\*LVP\*[A-Z0-9\*]+/g;

                    function walk(root) {
                        if (!root) return;
                        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null, false);
                        let node;
                        while (node = walker.nextNode()) {
                            const t = node.textContent.trim();
                            if (t.includes('DE*LVP') || t.includes('1/1') || t.includes('0/1') || t.includes('1 / 1') || t.includes('0 / 1')) {
                                nodes.push({
                                    text: t,
                                    ancestor: node.parentElement.closest('ion-item, .item-block, div[fittext]') || node.parentElement
                                });
                            }
                        }
                        Array.from(root.querySelectorAll('*')).forEach(el => {
                            if (el.shadowRoot) walk(el.shadowRoot);
                        });
                    }
                    walk(document.body);

                    const results = [];
                    const seenIds = new Set();
                    let currentId = null;
                    for (let i = 0; i < nodes.length; i++) {
                        const n = nodes[i];
                        const idMatch = n.text.match(idRegex);
                        if (idMatch) {
                            currentId = idMatch[0].trim().replace(/[^A-Z0-9\*]$/, '');
                            let status = "Unknown";
                            for (let j = i + 1; j < Math.min(i + 5, nodes.length); j++) {
                                const next = nodes[j];
                                if (next.text.includes('1 / 1') || next.text.includes('1/1')) { status = "Available"; break; }
                                if (next.text.includes('0 / 1') || next.text.includes('0/1')) { status = "Occupied"; break; }
                                if (next.text.includes('DE*LVP')) break;
                            }
                            if (!seenIds.has(currentId)) {
                                results.push({ id: currentId, status });
                                seenIds.add(currentId);
                            }
                        }
                    }
                    return results;
                }
JS

            if ($extraction && ref($extraction) eq 'ARRAY' && scalar @$extraction) {
                my $has_status = 0;
                for my $c (@$extraction) {
                    $has_status = 1 if $c->{status} ne 'Unknown';
                }

                if ($has_status) {
                    my @sorted = sort { $a->{id} cmp $b->{id} } @$extraction;
                    $self->{status_data}{connectors} = \@sorted;
                    $self->{status_data}{status} = "OK";
                    $self->{status_data}{error} = undef;
                    $self->_log("Extraction successful! Found " . scalar(@$extraction) . " connectors.");
                    goto FINISH;
                }
            }

            if ($cycle % 3 == 0) {
                $self->_log("Hydration stuck? Reloading station page...");
                $page->goto($self->{url}, { waitUntil => "load" });
                sleep(15);
            } else {
                sleep(8);
            }
        }
        $self->{status_data}{error} = "Data not found after 15 cycles.";
    };
    if ($@) {
        $self->_log("Scraper error: $@");
        $self->{status_data}{error} = "$@";
    }

FINISH:
    $self->{status_data}{last_updated} = DateTime->now->isoformat();
    eval { $context->close() if $context; };
    remove_tree($self->{user_data_dir});

    return $self->{status_data};
}

1;
