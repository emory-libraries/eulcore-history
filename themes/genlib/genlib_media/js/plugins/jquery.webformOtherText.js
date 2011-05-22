/**
* webformOtherText - hides/shows checkbox 'other' fields setup with webform module
*/

(function($){
$.fn.webformOtherText = function(options) {
	var defaults = { 
		checkId : $(this).attr('id'),
		textId : $(this).attr('id') + "-other"
	};
	// Extend our default options with those provided.
	var opts = $.extend(defaults, options);
	
	var idCheck = "#" + opts['checkId'];
	var idCheckWrap = idCheck + "-wrapper";
	var idText = "#" + opts['textId'];
	var idTextWrap = idText + "-wrapper";
	
	$(idCheckWrap).append($(idTextWrap));
	if (!$(idCheck).checked){ $(idTextWrap).hide(); }
    $(idCheck).click(function(){
      if(this.checked) {
        $(idText).removeAttr("readonly").removeAttr("disabled");
        $(idTextWrap).show();
      }
      else {
        $(idText).attr("readonly", "readonly").attr("disabled", "disabled");
        $(idTextWrap).hide();
      }
    })
};
})(jQuery);

/* usage -- TODO
$(document).ready(function(){ $('#edit-submitted-select-with-text-entry-databases').webformOtherText({ textId:'edit-submitted-specify-databases-used'}); });
 */
