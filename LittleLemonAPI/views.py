"""
Developed by: Shalee Khalil (shaleekhalil-dev)
Project: Little Lemon API - Meta Full Stack Specialization
Purpose: Implementation of RBAC, Search, Filtering, and Ordering for a Restaurant System.
Date: April 2026
"""

from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User, Group
from .models import MenuItem, Category, Cart, Order, OrderItem
from .serializers import MenuItemSerializer, CategorySerializer, CartSerializer, OrderSerializer
from datetime import date

# --- Category Views ---
class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

# --- Menu Item Views ---
class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'category__title']
    ordering_fields = ['price', 'category']

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminUser()]

class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAdminUser()]

# --- User Group Management (RBAC) ---
@api_view(['POST', 'DELETE'])
@permission_classes([IsAdminUser])
def managers(request):
    username = request.data.get('username')
    if username:
        user = get_object_or_404(User, username=username)
        managers_group = Group.objects.get(name="Manager")
        if request.method == 'POST':
            managers_group.user_set.add(user)
            return Response({"message": f"User {username} added to Manager group"}, status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            managers_group.user_set.remove(user)
            return Response({"message": f"User {username} removed from Manager group"}, status.HTTP_200_OK)
    return Response({"message": "Username is required"}, status.HTTP_400_BAD_REQUEST)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAdminUser])
def delivery_crew(request):
    username = request.data.get('username')
    if username:
        user = get_object_or_404(User, username=username)
        delivery_group = Group.objects.get(name="Delivery crew")
        if request.method == 'POST':
            delivery_group.user_set.add(user)
            return Response({"message": f"User {username} added to Delivery crew"}, status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            delivery_group.user_set.remove(user)
            return Response({"message": f"User {username} removed from Delivery crew"}, status.HTTP_200_OK)
    return Response({"message": "Username is required"}, status.HTTP_400_BAD_REQUEST)

# --- Cart System ---
class CartView(generics.ListCreateAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        menuitem_id = self.request.data.get('menuitem')
        item = get_object_or_404(MenuItem, id=menuitem_id)
        quantity = int(self.request.data.get('quantity'))
        unit_price = item.price
        price = quantity * unit_price
        serializer.save(user=self.request.user, unit_price=unit_price, price=price)

    def delete(self, request, *args, **kwargs):
        Cart.objects.filter(user=request.user).delete()
        return Response({"message": "Cart cleared successfully"}, status.HTTP_204_NO_CONTENT)

# --- Order Management ---
class OrdersView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name='Manager').exists():
            return Order.objects.all()
        if user.groups.filter(name='Delivery crew').exists():
            return Order.objects.filter(delivery_crew=user)
        return Order.objects.filter(user=user)

    def create(self, request, *args, **kwargs):
        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            return Response({"message": "Cart is empty"}, status.HTTP_400_BAD_REQUEST)

        total = sum([item.price for item in cart_items])
        order = Order.objects.create(user=request.user, status=False, total=total, date=date.today())

        for item in cart_items:
            OrderItem.objects.create(
                order=order, 
                menuitem=item.menuitem, 
                quantity=item.quantity, 
                unit_price=item.unit_price, 
                price=item.price
            )
            item.delete()

        return Response(OrderSerializer(order).data, status.HTTP_201_CREATED)

class SingleOrderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        user = self.request.user
        order = self.get_object()
        
        # Managers can update anything (assign delivery crew, etc.)
        if user.groups.filter(name='Manager').exists():
            return super().update(request, *args, **kwargs)
        
        # Delivery crew can ONLY update the 'status' field
        if user.groups.filter(name='Delivery crew').exists():
            if 'status' in request.data and len(request.data) == 1:
                return super().update(request, *args, **kwargs)
            return Response({"message": "You are only allowed to update order status"}, status.HTTP_403_FORBIDDEN)
            
        return Response({"message": "Access denied"}, status.HTTP_403_FORBIDDEN)