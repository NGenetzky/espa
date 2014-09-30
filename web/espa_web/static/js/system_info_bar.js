$(document).ready(function() {
    $('#ondemand-on').click(function(event) {
        if ($(this).hasClass('option-select')) {
            ; // do nothing
        } else {
            if (confirm('Enable ondemand ordering?')) {
                $.getJSON('/console/update-ondemand/on', function(data) {
                    if (data.result == 'success') {
                        $('#ondemand-on').toggleClass('option-select');
                        $('#ondemand-on').toggleClass('option-not-select');
                        $('#ondemand-off').toggleClass('option-select');
                        $('#ondemand-off').toggleClass('option-not-select');
                    } else {
                        alert('An error occurred: ' + data.message);
                    }
                });
            }
        }
    });
    $('#ondemand-off').click(function(event) {
        if ($(this).hasClass('option-select')) {
            ; // do nothing
        } else {
            if (confirm('Disable ondemand ordering?')) {
                $.getJSON('/console/update-ondemand/off', function(data) {
                    if (data.result == 'success') {
                        $('#ondemand-off').toggleClass('option-select');
                        $('#ondemand-off').toggleClass('option-not-select');
                        $('#ondemand-on').toggleClass('option-select');
                        $('#ondemand-on').toggleClass('option-not-select');
                    } else {
                        alert('An error occurred: ' + data.message);
                    }
                });
            }
        }
    });
});
