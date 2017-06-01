var now = moment();
// console.log("This is moment: ");
// console.log(now);
$('time').each(function(i, e) {
    var time = moment($(e).attr('datetime'));
    // console.log("time:");
    // console.log(time);
    // console.log("now.diff: ");
    // console.log(now.diff(time, 'days'));
    $(e).html('<span>' + time.from(now) + '</span>');
});

$('.fa-bell-o').click(function(){
    $("span.remove").remove()
});

$("#mark_read").on('click', function() {
    var pathname = window.location.pathname;
    var user_session = $(".hidden-xs").text();
    var celery_url = "/process" + pathname + "/" + user_session;
    $.get(celery_url);
    $('.notifications').attr('id', 'read');
    $('.notification-string').text('No New Notifications')
});