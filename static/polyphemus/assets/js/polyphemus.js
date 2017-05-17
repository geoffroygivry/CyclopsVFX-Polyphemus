var now = moment();
console.log("This is moment: ");
console.log(now);
$('time').each(function(i, e) {
    var time = moment($(e).attr('datetime'));
    console.log("time:");
    console.log(time);
    console.log("now.diff: ");
    console.log(now.diff(time, 'days'));
    $(e).html('<span>' + time.from(now) + '</span>');
});
