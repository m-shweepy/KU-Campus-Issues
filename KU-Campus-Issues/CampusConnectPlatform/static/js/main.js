// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Setup like buttons for AJAX interaction
    setupLikeButtons();
    
    // Setup image preview for issue submission
    setupImagePreview();
    
    // Setup comment form toggle
    setupCommentToggle();
    
    // Setup filter and sort controls
    setupFilters();
});

// Handle like button clicks with AJAX
function setupLikeButtons() {
    document.querySelectorAll('.like-button').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Get the issue ID from the data attribute
            const issueId = this.dataset.issueId;
            
            // Send AJAX request to like/unlike
            fetch(`/issue/${issueId}/like`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                },
                credentials: 'same-origin'
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                // Update like count
                const likeCountElement = document.querySelector(`#like-count-${issueId}`);
                if (likeCountElement) {
                    likeCountElement.textContent = data.likes;
                }
                
                // Update button appearance
                if (data.action === 'liked') {
                    this.innerHTML = '<i class="fas fa-heart"></i> Unlike';
                    this.classList.add('liked');
                } else {
                    this.innerHTML = '<i class="far fa-heart"></i> Like';
                    this.classList.remove('liked');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error processing your request. Please try again.');
            });
        });
    });
}

// Image preview functionality
function setupImagePreview() {
    const imageInput = document.getElementById('image');
    const imagePreview = document.getElementById('image-preview');
    
    if (imageInput && imagePreview) {
        imageInput.addEventListener('change', function() {
            const file = this.files[0];
            
            if (file) {
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    imagePreview.innerHTML = `
                        <div class="mt-2">
                            <p>Preview:</p>
                            <img src="${e.target.result}" class="img-fluid img-thumbnail" style="max-height: 200px">
                        </div>
                    `;
                }
                
                reader.readAsDataURL(file);
            } else {
                imagePreview.innerHTML = '';
            }
        });
    }
}

// Comment form toggle
function setupCommentToggle() {
    const commentToggle = document.getElementById('comment-toggle');
    const commentForm = document.getElementById('comment-form');
    
    if (commentToggle && commentForm) {
        commentToggle.addEventListener('click', function(e) {
            e.preventDefault();
            commentForm.classList.toggle('d-none');
            
            if (commentForm.classList.contains('d-none')) {
                this.textContent = 'Add Comment';
            } else {
                this.textContent = 'Cancel';
                document.getElementById('text').focus();
            }
        });
    }
}

// Setup filter and sort controls
function setupFilters() {
    const statusFilter = document.getElementById('status-filter');
    const sortBy = document.getElementById('sort-by');
    
    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            applyFilters();
        });
    }
    
    if (sortBy) {
        sortBy.addEventListener('change', function() {
            applyFilters();
        });
    }
}

// Apply filters and redirect
function applyFilters() {
    const statusFilter = document.getElementById('status-filter');
    const sortBy = document.getElementById('sort-by');
    
    let url = '/?';
    
    if (statusFilter && statusFilter.value !== 'all') {
        url += `status=${statusFilter.value}&`;
    }
    
    if (sortBy) {
        url += `sort=${sortBy.value}`;
    }
    
    window.location.href = url;
}

// Helper function to confirm deletions
function confirmDelete(issueId) {
    if (confirm('Are you sure you want to delete this issue? This action cannot be undone.')) {
        document.getElementById(`delete-form-${issueId}`).submit();
    }
}
