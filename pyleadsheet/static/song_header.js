function set_header_input_and_submit(input_id, new_value) {
    var element = document.getElementById(input_id);
    element.value = new_value;
    document.getElementById('header_html_form').submit();
}
