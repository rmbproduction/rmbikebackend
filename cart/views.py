from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Cart, CartItem, Order
from .serializers import (
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    OrderCreateSerializer
)

class CartViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user, is_active=True)

    def get_or_create_cart(self):
        cart, created = Cart.objects.get_or_create(
            user=self.request.user,
            is_active=True
        )
        return cart

    def list(self, request):
        cart = self.get_or_create_cart()
        serializer = self.get_serializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add_item(self, request):
        cart = self.get_or_create_cart()
        serializer = CartItemSerializer(data=request.data)
        
        if serializer.is_valid():
            part = serializer.validated_data['part']
            quantity = serializer.validated_data.get('quantity', 1)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                part=part,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            cart_serializer = self.get_serializer(cart)
            return Response(cart_serializer.data)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def update_item(self, request):
        cart = self.get_or_create_cart()
        serializer = CartItemSerializer(data=request.data)
        
        if serializer.is_valid():
            part = serializer.validated_data['part']
            quantity = serializer.validated_data['quantity']
            
            try:
                cart_item = CartItem.objects.get(cart=cart, part=part)
                cart_item.quantity = quantity
                cart_item.save()
                
                cart_serializer = self.get_serializer(cart)
                return Response(cart_serializer.data)
            except CartItem.DoesNotExist:
                return Response(
                    {"detail": "Item not found in cart"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        cart = self.get_or_create_cart()
        part_uuid = request.data.get('part')
        
        if not part_uuid:
            return Response(
                {"detail": "Part UUID is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            cart_item = CartItem.objects.get(cart=cart, part__uuid=part_uuid)
            cart_item.delete()
            
            cart_serializer = self.get_serializer(cart)
            return Response(cart_serializer.data)
        except CartItem.DoesNotExist:
            return Response(
                {"detail": "Item not found in cart"},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def clear(self, request):
        cart = self.get_or_create_cart()
        cart.items.all().delete()
        cart_serializer = self.get_serializer(cart)
        return Response(cart_serializer.data)

class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'uuid'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        # Return full order details after creation
        response_serializer = OrderSerializer(order)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, uuid=None):
        order = self.get_object()
        
        if order.status not in ['pending', 'processing']:
            return Response(
                {"detail": "Order cannot be cancelled in its current state"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Return items to stock
        for item in order.items.all():
            part = item.part
            part.stock_quantity += item.quantity
            part.save()
            
        order.status = 'cancelled'
        order.save()
        
        serializer = self.get_serializer(order)
        return Response(serializer.data) 