<%inherit file="local:templates.master"/>
<%namespace name="menu_items" file="tgext.crud.templates.menu_items"/>

<%def name="title()">
${tmpl_context.title} - ${model} Listing
</%def>
<%def name="meta()">
${menu_items.menu_style()}
<script>
    function crud_search_field_changed(select) {
        var selected = '';
        for (var idx=0; idx != select.options.length; ++idx) {
            if (select.options[idx].selected)
                selected = select.options[idx];
        }
        var field = document.getElementById('crud_search_value');
        field.name = selected.value;
    }
</script>
${parent.meta()}
</%def>
<%def name="body_class()">tundra</%def>
<div id="main_content">
  ${menu_items.menu_items()}
  <div id="crud_content">
    <h1>${model} Listing</h1>
    <div id="crud_btn_new">
      <a href='${tg.url("new", params=tmpl_context.kept_params)}' class="add_link">New ${model}</a>
         % if tmpl_context.paginators:
           <span>${tmpl_context.paginators.value_list.pager(link=mount_point+'/')}</span>
         % endif
      <div id="crud_search">
          <form>
              <select id="crud_search_field" onchange="crud_search_field_changed(this);">
                  % for field, name in headers:
                    % if field == selection[0]:
                      <option value="${field}" selected="selected">${name}</option>
                    % else:
                      <option value="${field}">${name}</option>
                    % endif
                  % endfor
              </select>
              <input id="crud_search_value" name="${selection[0]}" type="text" placeholder="equals" value="${selection[1]}" />
              <input type="submit" value="Search"/>
          </form>
      </div>
    </div>
    <div class="crud_table">
     ${tmpl_context.widget(value=value_list, action=mount_point+'.json', attrs=dict(style="height:200px; border:solid black 3px;")) |n}
    </div>
  </div>
  <div style="clear:both;"> &nbsp; </div>
</div>
