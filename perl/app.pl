use Mojolicious::Lite -signatures;
use lib 'lib';
use ChargerScraper;
use Text::CSV;
use DateTime;
use DateTime::Format::ISO8601;
use File::Path qw(make_path);
use JSON;
use Mojo::IOLoop;

my $VERSION = "1.2.0";
my $DATA_DIR = "data";
my $CSV_PATH = "$DATA_DIR/stations.csv";
my $STATION_BASE_URL = "https://ladeverbundplus.chargecloud.de/#/location/details/DE/LVP/";
my $DEFAULT_STATION_ID = "3411583";
my $PROVIDER_NAME = $ENV{PROVIDER_NAME} || "Erlanger Stadtwerke";
my $SCRAPE_INTERVAL = $ENV{SCRAPE_INTERVAL} || 300;
my $VERBOSE_LOGGING = ($ENV{VERBOSE_LOGGING} || 'false') eq 'true' ? 1 : 0;

# Global state
my $charger_data = {};
my $stations = [];
my $is_scraping = 0;

sub load_stations {
    make_path($DATA_DIR) unless -d $DATA_DIR;
    if (!-e $CSV_PATH) {
        $stations = [$DEFAULT_STATION_ID];
        save_stations();
    } else {
        my $csv = Text::CSV->new ({ binary => 1, auto_diag => 1 });
        open my $fh, "<:encoding(utf8)", $CSV_PATH or die "$CSV_PATH: $!";
        $stations = [];
        while (my $row = $csv->getline($fh)) {
            push @$stations, $row->[0] if $row->[0];
        }
        close $fh;
    }

    # Initialize charger_data
    for my $sid (@$stations) {
        $charger_data->{$sid} //= {
            status => "Starting",
            connectors => [],
            last_updated => undef,
            error => "Start up phase"
        };
    }
}

sub save_stations {
    make_path($DATA_DIR) unless -d $DATA_DIR;
    my $csv = Text::CSV->new ({ binary => 1, auto_diag => 1, eol => $/ });
    open my $fh, ">:encoding(utf8)", $CSV_PATH or die "$CSV_PATH: $!";
    for my $sid (@$stations) {
        $csv->print($fh, [$sid]);
    }
    close $fh;
}

sub perform_scrape_all {
    return if $is_scraping;
    $is_scraping = 1;

    my @current_stations = @$stations;

    # Use Mojo::IOLoop->subprocess to avoid blocking the main loop
    # We do them one by one to avoid overwhelming the system, matching python behavior
    Mojo::IOLoop->subprocess->run(sub {
        my $results = {};
        for my $sid (@current_stations) {
            my $url = "$STATION_BASE_URL$sid";
            my $scraper = ChargerScraper->new(
                url => $url,
                provider_name => $PROVIDER_NAME,
                verbose => $VERBOSE_LOGGING
            );
            eval {
                $results->{$sid} = $scraper->scrape();
            };
            if ($@) {
                $results->{$sid} = {
                    status => "Error",
                    error => "$@",
                    last_updated => DateTime->now->isoformat()
                };
            }
        }
        return $results;
    }, sub ($subprocess, $err, $results) {
        $is_scraping = 0;
        if ($err) {
            warn "Subprocess error: $err";
            return;
        }
        # Merge results back to global state
        for my $sid (keys %$results) {
            $charger_data->{$sid} = $results->{$sid};
        }
    });
}

# Helpers
helper german_ts => sub ($c, $ts_str) {
    return "Never" if !$ts_str;
    eval {
        my $dt = DateTime::Format::ISO8601->parse_datetime($ts_str);
        return $dt->strftime("%H:%Mh at %d.%m.%Y");
    };
    return $ts_str;
};

# Routes
get '/' => sub ($c) {
    $c->render(
        template => 'index',
        charger_data => $charger_data,
        is_scraping => $is_scraping,
        version => $VERSION
    );
} => 'index';

post '/add' => sub ($c) {
    my $sid = $c->param('station_id');
    $sid =~ s/^\s+|\s+$//g;
    if ($sid && !grep { $_ eq $sid } @$stations) {
        push @$stations, $sid;
        save_stations();
        $charger_data->{$sid} = { status => "Starting", connectors => [], last_updated => undef, error => "Added" };
        Mojo::IOLoop->next_tick(sub { perform_scrape_all() });
    }
    $c->redirect_to('/');
};

get '/remove/:station_id' => sub ($c) {
    my $sid = $c->stash('station_id');
    @$stations = grep { $_ ne $sid } @$stations;
    save_stations();
    delete $charger_data->{$sid};
    $c->redirect_to('/');
};

get '/status' => sub ($c) {
    $c->render(json => {
        version => $VERSION,
        stations => $charger_data,
        is_scraping => $is_scraping
    });
};

get '/refresh' => sub ($c) {
    Mojo::IOLoop->next_tick(sub { perform_scrape_all() });
    $c->redirect_to('/');
};

# Startup
load_stations();

# Periodic scrape
Mojo::IOLoop->recurring($SCRAPE_INTERVAL => sub {
    perform_scrape_all();
});

# Initial scrape
Mojo::IOLoop->timer(1 => sub {
    perform_scrape_all();
});

app->start;
