from django.db.models import Q


def apply_filters(queryset, data):
    """Narrow a queryset of Items using the cleaned filter-form data.
    Every filter is optional: an empty value is simply skipped."""

    # Keyword search: EVERY word must appear in the title,
    # description, brand or colour (case-insensitive)
    keyword = data.get('q', '').strip()
    for word in keyword.split():
        queryset = queryset.filter(
            Q(title__icontains=word)
            | Q(description__icontains=word)
            | Q(brand__icontains=word)
            | Q(color__icontains=word)
        )

    # Exact-match filters (these come from dropdowns)
    for field in ('item_type', 'category', 'location', 'status'):
        value = data.get(field)
        if value:
            queryset = queryset.filter(**{field: value})

    # Partial-match filters (free text)
    if data.get('color'):
        queryset = queryset.filter(color__icontains=data['color'].strip())
    if data.get('brand'):
        queryset = queryset.filter(brand__icontains=data['brand'].strip())

    # Date range
    if data.get('date_from'):
        queryset = queryset.filter(date__gte=data['date_from'])
    if data.get('date_to'):
        queryset = queryset.filter(date__lte=data['date_to'])

    return queryset