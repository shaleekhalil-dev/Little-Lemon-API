from rest_framework import generics, status, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User, Group
from .models import MenuItem, Category, Cart, Order, OrderItem
from .serializers import MenuItemSerializer, CategorySerializer, CartSerializer, OrderSerializer
from datetime import date

class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

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

@api_view(['POST', 'DELETE'])
@permission_classes([IsAdminUser])
def managers(request):
    username = request.data.get('username')
    if username:
        user = get_object_or_404(User, username=username)
        managers_group = Group.objects.get(name="Manager")
        if request.method == 'POST':
            managers_group.user_set.add(user)
            return Response({"message": "User added to Manager group"}, status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            managers_group.user_set.remove(user)
            return Response({"message": "User removed from Manager group"}, status.HTTP_200_OK)
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
            return Response({"message": "User added to Delivery crew"}, status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            delivery_group.user_set.remove(user)
            return Response({"message": "User removed from Delivery crew"}, status.HTTP_200_OK)
    return Response({"message": "Username is required"}, status.HTTP_400_BAD_REQUEST)

class CartView(generics.ListCreateAPIView):
    queryset = Cart.objects.all()
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
        return Response(status=status.HTTP_204_NO_CONTENT)

class OrdersView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
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
            OrderItem.objects.create(order=order, menuitem=item.menuitem, quantity=item.quantity, unit_price=item.unit_price, price=item.price)
            item.delete()

        return Response(OrderSerializer(order).data, status.HTTP_201_CREATED)

class SingleOrderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        user = self.request.user
        order = self.get_object()
        # المدير يمكنه إسناد عامل توصيل
        if user.groups.filter(name='Manager').exists():
            return super().update(request, *args, **kwargs)
        # عامل التوصيل يمكنه فقط تغيير حالة الطلب (Status)
        if user.groups.filter(name='Delivery crew').exists():
            if 'status' in request.data and len(request.data) == 1:
                return super().update(request, *args, **kwargs)
            return Response({"message": "You can only update the order status"}, status.HTTP_403_FORBIDDEN)
        return Response({"message": "Access denied"}, status.HTTP_403_FORBIDDEN)