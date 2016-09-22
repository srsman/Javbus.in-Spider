var page = require('webpage').create(),
    system = require('system'),
    address;

phantom.outputEncoding = 'UTF-8';

if (system.args.length === 1) {
    console.log('args error')
    phantom.exit(1);
} else {
    url = system.args[1];

    page.onConsoleMessage = function(msg) {
        console.log(msg)
    };

    page.open(url, function (status) {

        if (status === 'success') {
            page.evaluate(function() {
                var magnet_table = document.getElementById('magnet-table');
                var trs = magnet_table.getElementsByTagName('tr');
                if (trs.length == 1) {
                    phantom.exit();
                }
                for (i = 1; i < trs.length; i++) {
                    var tds = trs[i].getElementsByTagName('td');
                    var a = tds[0].getElementsByTagName('a');
                    console.log(a[0].getAttribute('href'));
                }
            });
        } else {
            console.log('error');
        }

        phantom.exit();
    }

    )
}
