/**
* inputTip - puts helper text in an input field
*/
(function($){
$.fn.inputTip = function(options) {
	var defaults = { /* no options for now */  };
	// Extend our default options with those provided.
	var opts = $.extend(defaults, options);
	$(this).focus(function(){
		if ($(this).val() == $(this).attr('alt')) {
			$(this).val('');
		}
	});
	$(this).blur(function(){
		if ($(this).val() == '') {
			$(this).val($(this).attr('alt'));
		}
	});
	$(this).blur();
};
})(jQuery);
/* usage -- just initialize fields like this and you're set - your field should have an alt tag
$(document).ready(function(){ $('#ballardSearch input:text').inputTip(); });
 */
