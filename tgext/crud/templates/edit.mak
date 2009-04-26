<%inherit file="local:templates.master"/>
<%namespace name="menu_items" file="tgext.crud.templates.menu_items"/>

<%def name="title()">
<title>TurboGears Admin System - ${model}</title>
${menu_items.menu_style()}
</%def>

<%def name="body_class()">tundra</%def>
<%def name="content()">
  <div id="main_content">
    ${menu_items.sub_menu_items()}
  <div style="float:left;">
    <h2 style="margin-top:1px;">Edit ${model}</h2>
     ${tmpl_context.widget(value=value, action='./') | n}
  </div>
  <div style="height:0px; clear:both;"> &nbsp; </div>
</%def>
