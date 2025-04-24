from flask import Blueprint, jsonify, request
from models import db, InventoryItem, Transaction, Category, NotificationSetting
from functools import wraps
from datetime import datetime

api = Blueprint('api', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permissions):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_permissions = session.get('user', {}).get('permissions', [])
            if not any(perm in user_permissions for perm in permissions):
                return jsonify({'error': 'Permission denied'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Inventory Endpoints
@api.route('/inventory', methods=['GET'])
@login_required
@permission_required(['read_inventory'])
def get_inventory():
    items = InventoryItem.query.all()
    return jsonify([{
        'id': item.id,
        'item_id': item.item_id,
        'name': item.name,
        'quantity': item.quantity,
        'category': item.category,
        'min_threshold': item.min_threshold,
        'last_update': item.last_update.isoformat()
    } for item in items])

@api.route('/inventory/<item_id>', methods=['GET'])
@login_required
@permission_required(['read_inventory'])
def get_item(item_id):
    item = InventoryItem.query.filter_by(item_id=item_id).first_or_404()
    return jsonify({
        'id': item.id,
        'item_id': item.item_id,
        'name': item.name,
        'quantity': item.quantity,
        'category': item.category,
        'min_threshold': item.min_threshold,
        'last_update': item.last_update.isoformat()
    })

@api.route('/inventory', methods=['POST'])
@login_required
@permission_required(['write_all'])
def create_item():
    data = request.get_json()
    item = InventoryItem(
        item_id=data['item_id'],
        name=data['name'],
        quantity=data.get('quantity', 0),
        category=data.get('category'),
        min_threshold=data.get('min_threshold', 10),
        added_by=session['user']['username']
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'message': 'Item created successfully'}), 201

# Transaction Endpoints
@api.route('/transactions', methods=['GET'])
@login_required
@permission_required(['read_all'])
def get_transactions():
    transactions = Transaction.query.all()
    return jsonify([{
        'id': t.id,
        'type': t.type,
        'item_id': t.item_id,
        'quantity': t.quantity,
        'user': t.user,
        'timestamp': t.timestamp.isoformat(),
        'status': t.status
    } for t in transactions])

@api.route('/transactions', methods=['POST'])
@login_required
@permission_required(['create_transaction'])
def create_transaction():
    data = request.get_json()
    transaction = Transaction(
        type=data['type'],
        item_id=data['item_id'],
        quantity=data['quantity'],
        user=session['user']['username'],
        notes=data.get('notes')
    )
    db.session.add(transaction)
    
    # Update inventory quantity
    item = InventoryItem.query.filter_by(item_id=data['item_id']).first_or_404()
    if data['type'] == 'masuk':
        item.quantity += data['quantity']
    else:
        if item.quantity < data['quantity']:
            return jsonify({'error': 'Insufficient stock'}), 400
        item.quantity -= data['quantity']
    
    db.session.commit()
    return jsonify({'message': 'Transaction created successfully'}), 201

# Approval Endpoints
@api.route('/approvals', methods=['GET'])
@login_required
@permission_required(['approve_transactions'])
def get_pending_approvals():
    pending = Transaction.query.filter_by(status='pending').all()
    return jsonify([{
        'id': t.id,
        'type': t.type,
        'item_id': t.item_id,
        'quantity': t.quantity,
        'user': t.user,
        'timestamp': t.timestamp.isoformat()
    } for t in pending])

@api.route('/approvals/<int:transaction_id>', methods=['PUT'])
@login_required
@permission_required(['approve_transactions'])
def approve_transaction(transaction_id):
    data = request.get_json()
    transaction = Transaction.query.get_or_404(transaction_id)
    transaction.status = data['status']  # 'approved' or 'rejected'
    transaction.approved_by = session['user']['username']
    transaction.approved_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': f'Transaction {data["status"]} successfully'})

# Analytics Endpoints
@api.route('/analytics/summary', methods=['GET'])
@login_required
@permission_required(['view_analytics'])
def get_analytics_summary():
    total_items = InventoryItem.query.count()
    low_stock = InventoryItem.query.filter(
        InventoryItem.quantity <= InventoryItem.min_threshold
    ).count()
    recent_transactions = Transaction.query.order_by(
        Transaction.timestamp.desc()
    ).limit(5).all()
    
    return jsonify({
        'total_items': total_items,
        'low_stock_count': low_stock,
        'recent_transactions': [{
            'type': t.type,
            'item_id': t.item_id,
            'quantity': t.quantity,
            'timestamp': t.timestamp.isoformat()
        } for t in recent_transactions]
    })

# Category Endpoints
@api.route('/categories', methods=['GET'])
@login_required
def get_categories():
    categories = Category.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'description': c.description
    } for c in categories])

@api.route('/categories', methods=['POST'])
@login_required
@permission_required(['manage_categories'])
def create_category():
    data = request.get_json()
    category = Category(
        name=data['name'],
        description=data.get('description', '')
    )
    db.session.add(category)
    db.session.commit()
    return jsonify({'message': 'Category created successfully'}), 201

# Notification Settings Endpoints
@api.route('/notification-settings', methods=['GET'])
@login_required
def get_notification_settings():
    settings = NotificationSetting.query.filter_by(
        user_id=session['user']['id']
    ).first()
    if not settings:
        return jsonify({})
    return jsonify({
        'email_notifications': settings.email_notifications,
        'notification_frequency': settings.notification_frequency,
        'low_stock_threshold': settings.low_stock_threshold
    })

@api.route('/notification-settings', methods=['PUT'])
@login_required
@permission_required(['manage_notifications'])
def update_notification_settings():
    data = request.get_json()
    settings = NotificationSetting.query.filter_by(
        user_id=session['user']['id']
    ).first()
    if not settings:
        settings = NotificationSetting(user_id=session['user']['id'])
        db.session.add(settings)
    
    settings.email_notifications = data.get('email_notifications', True)
    settings.notification_frequency = data.get('notification_frequency', 'daily')
    settings.low_stock_threshold = data.get('low_stock_threshold', 10)
    
    db.session.commit()
    return jsonify({'message': 'Settings updated successfully'}) 