from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem
from spare_parts.serializers import SparePartListSerializer

class CartItemSerializer(serializers.ModelSerializer):
    part_details = SparePartListSerializer(source='part', read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
        source='get_total_price'
    )

    class Meta:
        model = CartItem
        fields = ['uuid', 'part', 'part_details', 'quantity', 'total_price']
        read_only_fields = ['uuid']

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value

    def validate(self, data):
        part = data.get('part')
        quantity = data.get('quantity', 1)
        
        if part and not part.is_active:
            raise serializers.ValidationError("This part is not available for purchase")
        
        if part and quantity > part.stock_quantity:
            raise serializers.ValidationError(f"Only {part.stock_quantity} units available in stock")
        
        return data

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
        source='get_total_price'
    )
    total_items = serializers.IntegerField(
        read_only=True,
        source='get_total_items'
    )

    class Meta:
        model = Cart
        fields = ['uuid', 'items', 'total_price', 'total_items', 'created_at', 'updated_at']
        read_only_fields = ['uuid']

class OrderItemSerializer(serializers.ModelSerializer):
    part_details = SparePartListSerializer(source='part', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['uuid', 'part', 'part_details', 'quantity', 'price', 'total']
        read_only_fields = ['uuid', 'price', 'total']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'uuid', 'order_number', 'status', 'payment_status',
            'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_pincode', 'shipping_phone',
            'total_amount', 'shipping_charges', 'tax_amount',
            'discount_amount', 'final_amount',
            'tracking_number', 'notes', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'order_number', 'total_amount', 'final_amount',
            'tracking_number'
        ]

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating orders from cart"""
    class Meta:
        model = Order
        fields = [
            'shipping_address', 'shipping_city', 'shipping_state',
            'shipping_pincode', 'shipping_phone'
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        cart = Cart.objects.get(user=user, is_active=True)
        
        if not cart.items.exists():
            raise serializers.ValidationError("Cart is empty")
        
        # Calculate order totals
        total_amount = cart.get_total_price()
        shipping_charges = 0  # You can implement your shipping calculation logic
        tax_amount = total_amount * 0.18  # Assuming 18% tax
        final_amount = total_amount + shipping_charges + tax_amount
        
        # Create order
        order = Order.objects.create(
            user=user,
            total_amount=total_amount,
            shipping_charges=shipping_charges,
            tax_amount=tax_amount,
            final_amount=final_amount,
            **validated_data
        )
        
        # Create order items from cart items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                part=cart_item.part,
                quantity=cart_item.quantity,
                price=cart_item.part.get_effective_price(),
                total=cart_item.get_total_price()
            )
            
            # Update stock quantity
            part = cart_item.part
            part.stock_quantity -= cart_item.quantity
            part.save()
        
        # Clear the cart
        cart.delete()
        
        return order 