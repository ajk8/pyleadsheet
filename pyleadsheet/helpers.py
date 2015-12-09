def get_sortable_title(title):
    if title.lower().startswith('the '):
        title = ' '.join(title.split()[1:])
    return title
