import os
import uuid
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from app import app, db
from models import User, Issue, Like
from forms import LoginForm, RegisterForm, IssueForm, UpdateIssueStatusForm
from helpers import save_image

# Home page - shows all issues
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', None)
    sort_by = request.args.get('sort', 'newest')
    
    # Base query
    query = Issue.query
    
    # Apply status filter if provided
    if status_filter and status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    # Apply sorting
    if sort_by == 'oldest':
        query = query.order_by(Issue.created_at.asc())
    elif sort_by == 'most_likes':
        # This is a simple approach - in a real app with many likes, you'd want to optimize this
        query = query.order_by(Issue.id.desc())  # Temp ordering, will be resorted after fetching
    else:  # Default to newest
        query = query.order_by(Issue.created_at.desc())
    
    # Pagination
    issues = query.paginate(page=page, per_page=10)
    
    # If sorting by likes, we need to resort after database fetch
    if sort_by == 'most_likes':
        # Convert pagination object to list, sort, then create a new pagination-like object
        issues_list = list(issues.items)
        issues_list.sort(key=lambda x: x.like_count, reverse=True)
        # We're not implementing a proper pagination class here, just carrying over the items
        issues.items = issues_list
    
    return render_template(
        'index.html', 
        issues=issues, 
        current_filter=status_filter or 'all',
        current_sort=sort_by
    )

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = User(
            username=form.username.data,
            email=form.email.data,
            password_hash=hashed_password
        )
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            
            # Redirect admins to admin dashboard
            if user.is_admin:
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('index'))
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    
    return render_template('login.html', form=form)

# Admin login
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            flash('You do not have admin privileges.', 'warning')
            return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            if user.is_admin:
                login_user(user)
                flash('Admin login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('This account does not have admin privileges.', 'danger')
        else:
            flash('Login unsuccessful. Please check username and password.', 'danger')
    
    return render_template('admin_login.html', form=form)

# User logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Post a new issue
@app.route('/post', methods=['GET', 'POST'])
@login_required
def post_issue():
    form = IssueForm()
    if form.validate_on_submit():
        image_filename = None
        
        # Handle image upload if provided
        if form.image.data:
            image_filename = save_image(form.image.data)
            
        issue = Issue(
            title=form.title.data,
            description=form.description.data,
            location=form.location.data,
            image_filename=image_filename,
            user_id=current_user.id
        )
        
        db.session.add(issue)
        db.session.commit()
        flash('Your issue has been posted!', 'success')
        return redirect(url_for('index'))
    
    return render_template('post_issue.html', form=form)

# View a specific issue
@app.route('/issue/<int:issue_id>', methods=['GET'])
def issue_details(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    
    # Check if current user has liked this issue
    user_liked = False
    if current_user.is_authenticated:
        like = Like.query.filter_by(user_id=current_user.id, issue_id=issue.id).first()
        user_liked = like is not None
    
    # If the user is an admin, provide a form to update the issue status
    status_form = None
    if current_user.is_authenticated and current_user.is_admin:
        status_form = UpdateIssueStatusForm()
        status_form.status.data = issue.status
    
    return render_template(
        'issue_details.html', 
        issue=issue,
        user_liked=user_liked,
        status_form=status_form
    )

# Like an issue
@app.route('/issue/<int:issue_id>/like', methods=['POST'])
@login_required
def like_issue(issue_id):
    issue = Issue.query.get_or_404(issue_id)
    
    # Check if user already liked this issue
    existing_like = Like.query.filter_by(user_id=current_user.id, issue_id=issue.id).first()
    
    if existing_like:
        # Remove the like if already liked
        db.session.delete(existing_like)
        action = 'unliked'
    else:
        # Add a new like
        like = Like(user_id=current_user.id, issue_id=issue.id)
        db.session.add(like)
        action = 'liked'
    
    db.session.commit()
    
    # Get updated like count
    likes_count = Like.query.filter_by(issue_id=issue.id).count()
    
    # If this was an AJAX request, return JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return {
            'likes': likes_count,
            'action': action
        }
    
    # Otherwise redirect back to the issue
    flash(f'You have {action} this issue.', 'success')
    return redirect(url_for('issue_details', issue_id=issue.id))

# Update issue status (admin only)
@app.route('/issue/<int:issue_id>/status', methods=['POST'])
@login_required
def update_issue_status(issue_id):
    if not current_user.is_admin:
        abort(403)  # Forbidden
    
    issue = Issue.query.get_or_404(issue_id)
    form = UpdateIssueStatusForm()
    
    if form.validate_on_submit():
        issue.status = form.status.data
        issue.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Issue status has been updated.', 'success')
    
    return redirect(url_for('issue_details', issue_id=issue.id))

# Admin dashboard
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)  # Forbidden
    
    # Get statistics for the dashboard
    total_issues = Issue.query.count()
    new_issues = Issue.query.filter_by(status='new').count()
    in_progress_issues = Issue.query.filter_by(status='in progress').count()
    resolved_issues = Issue.query.filter_by(status='resolved').count()
    
    # Get recent issues for quick moderation
    recent_issues = Issue.query.order_by(Issue.created_at.desc()).limit(10).all()
    
    return render_template(
        'admin.html',
        total_issues=total_issues,
        new_issues=new_issues,
        in_progress_issues=in_progress_issues,
        resolved_issues=resolved_issues,
        recent_issues=recent_issues
    )

# Delete an issue (admin only)
@app.route('/issue/<int:issue_id>/delete', methods=['POST'])
@login_required
def delete_issue(issue_id):
    if not current_user.is_admin:
        abort(403)  # Forbidden
    
    issue = Issue.query.get_or_404(issue_id)
    
    # Delete the associated image if it exists
    if issue.image_filename:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], issue.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            app.logger.error(f"Error deleting image: {e}")
    
    db.session.delete(issue)
    db.session.commit()
    
    flash('Issue has been deleted.', 'success')
    
    # Check if we came from the admin dashboard
    if request.referrer and '/admin' in request.referrer:
        return redirect(url_for('admin_dashboard'))
    
    return redirect(url_for('index'))

# Add admin initialization route (development only)
@app.route('/init_admin')
def init_admin():
    # Check if admin already exists
    admin = User.query.filter_by(is_admin=True).first()
    if admin:
        flash('Admin already exists.', 'info')
        return redirect(url_for('index'))
    
    # Create admin user (in production, use stronger password and ENV vars)
    password = "admin123"  # This should come from ENV in production
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=generate_password_hash(password),
        is_admin=True
    )
    
    db.session.add(admin)
    db.session.commit()
    
    flash(f'Admin user created with username: admin and password: {password}', 'success')
    return redirect(url_for('index'))
