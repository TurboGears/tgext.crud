<%def name="menu_style()">
<style>
#menu_items {
  padding:0px 12px 0px 2px;
  list-style-type:None;
  float:left; 
  padding-left:0px;
  }
</style>
</%def>

<%def name="menu_items(path='../')">
    <div id="menu_items">
        <ul>
        % if hasattr(tmpl_context, 'menu_items'):
           % for lower, item in sorted(tmpl_context.menu_items.iteritems()):
            <li><a href="${path}${lower}s">${item.__name__}</a></li>
           % endfor
        % endif
        </ul>
    </div>
</%def>