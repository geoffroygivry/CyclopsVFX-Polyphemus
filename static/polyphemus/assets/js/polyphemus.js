var now = moment();

$('time').each(function(i, e) {
    var time = moment($(e).attr('datetime'));
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

$(document).ready(function () {
                $(document).on('mouseenter', '.cover-photo-shot', function () {
                    $(this).find(":button").show();
                }).on('mouseleave', '.cover-photo-shot', function () {
                    $(this).find(":button").hide();
                });
            });

$(document).on("click", ".delete-shot", function () {
     var shotName = $(this).data('id');
     console.log("test:");
     console.log(shotName);
     $("#cyc-entity").html("<strong>" + shotName + "</strong>");
});
