from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from matcher.services.matching_service import find_visible_matches

from .filters import apply_filters
from .forms import ItemFilterForm, ItemForm
from .models import Item

ITEMS_PER_PAGE = 9


@login_required
def report_lost(request):
    if request.method == 'POST':
        # request.FILES carries the uploaded photo
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)  # build the Item, don't save yet
            item.user = request.user        # owner = logged-in user
            item.item_type = Item.LOST
            item.status = Item.LOST
            item.save()
            match_count = len(find_visible_matches(item))  # Run the matching engine
            if match_count:
                messages.success(request, f'Report saved. We found {match_count} possible match(es)!')
                return redirect('item_matches', pk=item.pk)
            messages.success(request, 'Your lost item report has been saved.')
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemForm()

    return render(request, 'items/item_form.html',
                  {'form': form, 'heading': 'Report a lost item'})


@login_required
def my_reports(request):
    items = Item.objects.filter(user=request.user)
    return render(request, 'items/my_reports.html', {'items': items})


@login_required
def item_detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    return render(request, 'items/item_detail.html', {'item': item})


@login_required
def item_edit(request, pk):
    # user=request.user means only the OWNER can find this item here
    item = get_object_or_404(Item, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Report updated.')
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemForm(instance=item)

    return render(request, 'items/item_form.html',
                  {'form': form, 'heading': 'Edit report'})


@login_required
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk, user=request.user)

    if request.method == 'POST':
        if item.image:
            item.image.delete(save=False)  # remove the photo file from disk too
        item.delete()
        messages.success(request, 'Report deleted.')
        return redirect('my_reports')

    return render(request, 'items/item_confirm_delete.html', {'item': item})


@login_required
@require_POST  # only accepts a form submit, never a plain link
def item_change_status(request, pk):
    item = get_object_or_404(Item, pk=pk, user=request.user)
    new_status = request.POST.get('status')

    # Owners may only choose these two. The system sets the others later.
    if new_status in (Item.RECOVERED, Item.CLOSED):
        item.status = new_status
        item.save()
        messages.success(request, f'Report marked as {item.get_status_display()}.')
    else:
        messages.error(request, 'That status is not allowed.')

    return redirect('item_detail', pk=item.pk)

@login_required
def report_found(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, item_type=Item.FOUND)
        if form.is_valid():
            item = form.save(commit=False)
            item.user = request.user
            item.item_type = Item.FOUND
            item.status = Item.FOUND
            item.save()
            match_count = len(find_visible_matches(item))  # run the matching engine
            if match_count:
                messages.success(
                    request, f'Report saved. We found {match_count} possible match(es)!')
                return redirect('item_matches', pk=item.pk)
            messages.success(request, 'Your found item report has been saved.')
            return redirect('item_detail', pk=item.pk)
    else:
        form = ItemForm(item_type=Item.FOUND)

    note = ('Describe the item in general terms. Keep one or two special details '
            '(a serial number, a sticker, what is inside) to yourself. '
            'They will be used later to check that the real owner is claiming it.')

    return render(request, 'items/item_form.html',
                  {'form': form, 'heading': 'Report a found item', 'note': note})

@login_required
def browse_items(request):
    form = ItemFilterForm(request.GET or None)  # GET: filters stay in the URL
    items = Item.objects.all()

    if form.is_bound:
        if form.is_valid():
            items = apply_filters(items, form.cleaned_data)
        else:
            items = items.none()  # invalid filters: show no results, plus the errors

    paginator = Paginator(items, ITEMS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Keep the filters when moving between pages (everything except "page")
    params = request.GET.copy()
    params.pop('page', None)

    return render(request, 'items/browse.html', {
        'form': form,
        'page_obj': page_obj,
        'total': paginator.count,
        'query_string': params.urlencode(),
    })