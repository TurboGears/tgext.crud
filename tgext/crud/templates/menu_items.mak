<%def name="menu_style()">
<style>
    ${tmpl_context.crud_style}
</style>
</%def>

<%def name="menu_items(pk_count=0)">
  <div id="crud_leftbar">
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
  </div>
</%def>