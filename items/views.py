from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ItemForm
from .models import Item


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