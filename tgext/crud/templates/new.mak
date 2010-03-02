<%inherit file="local:templates.master"/>
<%namespace name="menu_items" file="tgext.crud.templates.menu_items"/>

<%def name="title()">
${tmpl_context.title} - New ${model}
</%def>
<%def name="header()">
  ${menu_items.menu_style()}
  ${parent.header()}
</%def>

<%def name="body_class()">tundra</%def>

<div id="main_content">
  ${menu_items.menu_items('../')}
<div style="float:left;" class="crud_add">
  <h2 style="margin:5px 0px; 4px; 0px;">New ${model}</h2>
   ${tmpl_context.widget(value=value, action='./') | n}
</div>
<div style="height:0px; clear:both;"> &nbsp; </div>
