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

<%def name="menu_items(pk_count=0)">
    <div id="menu_items">
        <ul>
        % if hasattr(tmpl_context, 'menu_items'):
           % for lower, item in sorted(tmpl_context.menu_items.iteritems()):
            <li>
                <a href="${tmpl_context.crud_helpers.make_link(lower, pk_count)}">${item}</a>
            </li>
           % endfor
        % endif
        </ul>
    </div>
</%def>