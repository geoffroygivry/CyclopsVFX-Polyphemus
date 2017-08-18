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

var items = $(".hidden-seq-shots").text();


// $(function(){
//     var temp = {};

//     $.each(items, function(){
//         $("<option />")
//         .attr("value", this.value)
//         .html(this.name)
//         .appendTo("#firstmenu");
//         temp[this.value] = this.subitems;
//     });

//     $("#firstmenu").change(function(){
//         var value = $(this).val();
//         var menu = $("#secondmenu");

//         menu.empty();
//         $.each(temp[value], function(){
//             $("<option />")
//             .attr("value", this.value)
//             .html(this.name)
//             .appendTo(menu);
//         });
//     }).change();


// });
