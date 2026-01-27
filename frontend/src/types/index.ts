export interface OrderItem {
    id: string;
    sku: string;
    product_name: string;
    quantity: number;
    unit_price: number;
    line_total: number;
    line_type: string;
}

export interface Order {
    id: string;
    external_order_id: string;
    channel_code: string;
    customer_name: string;
    customer_phone: string;
    total_amount: number;
    status_normalized: string;
    payment_status: string;
    created_at: string;
    order_datetime?: string;
    customer_address?: string;
    subtotal_amount?: number;
    discount_amount?: number;
    shipping_fee?: number;
    payment_method?: string;
    order_updated_at?: string;
    tracking_number?: string;
    rts_time?: string;
    items: OrderItem[];
}

export interface Product {
    id: string;
    sku: string;
    name: string;
    product_type: string;
    standard_cost: number;
    standard_price: number;
    image_url?: string;
    is_active: boolean;
    stock_quantity?: number;  // Available stock
    on_hand?: number;         // Total on hand
    reserved?: number;        // Reserved for orders
}

export interface StockSummary {
    product_id: string;
    sku: string;
    product_name: string;
    on_hand: number;
    allocated: number;
    available: number;
}

export interface StockMovement {
    id: string;
    sku: string;
    movement_type: string;
    quantity: number;
    reference_type: string;
    note: string;
    created_at: string;
}

export interface PlatformConfig {
    id: string;
    platform: string;
    shop_name: string;
    is_active: boolean;
    sync_enabled: boolean;
    last_sync_at?: string;
}

export interface Promotion {
    id: string;
    name: string;
    condition_type: string;
    is_active: boolean;
    start_at?: string;
    end_at?: string;
    description?: string;
    discount_value?: number;
    min_order_amount?: number;
    max_discount?: number;
    applicable_skus?: string[];
    channels?: string[];
}

export interface ApiResponse<T> {
    data: T;
    total?: number;
    page?: number;
    per_page?: number;
}
