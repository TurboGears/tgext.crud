<%inherit file="app:templates.master"/>
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
    <h1 style="margin:5px 0px; 4px; 0px;">New ${model}</h1>
     ${tmpl_context.widget(value=value, action='./') | n}
  </div>
  <div style="height:0px; clear:both;"> &nbsp; </div>
</%def>