(function(a){a(document).ready(function(){a(".reload-form").ReloadForm();a(".reload-link").reloadLink();a(".editable").each(function(){var b=a(this);b.find("span").EditableField({editLink:b.find(".edit-link"),hoverShowContainer:".attribute-table"})})})})(jQuery);
