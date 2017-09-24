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
console.log(items);


// $(function(){
//     var temp = {};

//     $.each(items, function(){
//         $("<option />")
//         .attr("name", this.value)
//         .html(this.name)
//         .appendTo("#firstmenu");
//         temp[this.value] = this.shots;
//     });
//     console.log(temp);
//     $("#firstmenu").change(function(){
//         var value = $(this).val();
//         var menu = $("#secondmenu");

//         menu.empty();
//         $.each(temp[value], function(){
//             $("<option />")
//             .attr("name", this.value)
//             .html(this.name)
//             .appendTo(menu);
//         });
//     }).change();


// });


(function(){
    'use strict';
    var $ = jQuery;
    $.fn.extend({
        filterTable: function(){
            return this.each(function(){
                $(this).on('keyup', function(e){
                    $('.filterTable_no_results').remove();
                    var $this = $(this), 
                        search = $this.val().toLowerCase(), 
                        target = $this.attr('data-filters'), 
                        $target = $(target), 
                        $rows = $target.find('tbody tr');
                        
                    if(search == '') {
                        $rows.show(); 
                    } else {
                        $rows.each(function(){
                            var $this = $(this);
                            $this.text().toLowerCase().indexOf(search) === -1 ? $this.hide() : $this.show();
                        })
                        if($target.find('tbody tr:visible').size() === 0) {
                            var col_count = $target.find('tr').first().find('td').size();
                            var no_results = $('<tr class="filterTable_no_results"><td colspan="'+col_count+'">No results found</td></tr>')
                            $target.find('tbody').append(no_results);
                        }
                    }
                });
            });
        }
    });
    $('[data-action="filter"]').filterTable();
})(jQuery);

$(function(){
    // attach table filter plugin to inputs
    $('[data-action="filter"]').filterTable();
    
    $('.container').on('click', '.panel-heading span.filter', function(e){
        var $this = $(this), 
            $panel = $this.parents('.panel');
        
        $panel.find('.panel-body').slideToggle();
        if($this.css('display') != 'none') {
            $panel.find('.panel-body input').focus();
        }
    });
    $('[data-toggle="tooltip"]').tooltip();
})