// main.js

let selectedStudentIds = new Set(); // Using a Set for efficient ID management

function openModal(mode, id = null, name = '', subject = '', marks = '') {
    document.getElementById('modal').style.display = 'flex'; // Use flex to center
    document.getElementById('name').value = name;
    document.getElementById('subject').value = subject;
    document.getElementById('marks').value = marks;

    const modalSubmitBtn = document.getElementById('modalSubmitBtn');

    if (mode === 'add') {
        modalSubmitBtn.onclick = submitForm;
        document.querySelector('.modal-content h3').textContent = 'Add New Student';
        modalSubmitBtn.textContent = 'Add'; // Set button text for Add mode
        // Clear fields for add mode
        document.getElementById('name').value = '';
        document.getElementById('subject').value = '';
        document.getElementById('marks').value = '';
    } else if (mode === 'edit') {
        modalSubmitBtn.onclick = function() { editStudentData(id); };
        document.querySelector('.modal-content h3').textContent = 'Edit Student';
        modalSubmitBtn.textContent = 'Update'; // Set button text for Edit mode
    }
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

function showNotification(message, isError = false) {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    if (isError) {
        notification.classList.add('error');
    } else {
        notification.classList.remove('error');
    }
    notification.style.display = 'block';
    setTimeout(() => {
        notification.style.display = 'none';
    }, 3000); // Hide after 3 seconds
}

function submitForm() {
    fetch('/add/', {
        method: 'POST',
        headers: {'X-CSRFToken': getCSRFToken(), 'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams({
            name: document.getElementById('name').value,
            subject: document.getElementById('subject').value,
            marks: document.getElementById('marks').value
        })
    }).then(res => res.json()).then(data => {
        if (data.success) {
            closeModal();
            showNotification('Student added successfully!');
            location.reload(); // Reload to reflect addition
        } else {
            showNotification('Failed to add student.', true);
        }
    }).catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred during addition.', true);
    });
}

function deleteStudent(id) {
    if (!confirm('Are you sure you want to delete this student?')) {
        return;
    }
    fetch(`/delete/${id}/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCSRFToken()}
    }).then(res => res.json()).then(data => {
        if (data.success) {
            showNotification('Student deleted successfully!');
            location.reload(); // Reload to reflect deletion
        } else {
            showNotification('Failed to delete student.', true);
        }
    }).catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred during deletion.', true);
    });
}

function editStudent(id, name, subject, marks) {
    openModal('edit', id, name, subject, marks);
}

function editStudentData(id) {
    fetch(`/edit/${id}/`, {
        method: 'POST',
        headers: {'X-CSRFToken': getCSRFToken(), 'Content-Type': 'application/x-www-form-urlencoded'},
        body: new URLSearchParams({
            name: document.getElementById('name').value,
            subject: document.getElementById('subject').value,
            marks: document.getElementById('marks').value
        })
    }).then(res => res.json()).then(data => {
        if (data.success) {
            closeModal();
            showNotification('Student updated successfully!');
            location.reload(); // Reload to see the updated data
        } else {
            showNotification('Failed to update student.', true);
        }
    }).catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred during update.', true);
    });
}

function getCSRFToken() {
    return document.cookie.split('; ').find(row => row.startsWith('csrftoken')).split('=')[1];
}

// New function for search and filter
function applyFilters() {
    const searchInput = document.getElementById('search-input').value;
    const subjectFilter = document.getElementById('subject-filter').value;

    let url = new URL(window.location.href.split('?')[0]); // Base URL
    if (searchInput) {
        url.searchParams.set('search', searchInput);
    } else {
        url.searchParams.delete('search');
    }
    if (subjectFilter && subjectFilter !== 'all') {
        url.searchParams.set('subject', subjectFilter);
    } else {
        url.searchParams.delete('subject');
    }
    window.location.href = url.toString();
}

// --- Multiple Select and Delete Functions ---

document.addEventListener('DOMContentLoaded', function() {
    const selectAllCheckbox = document.getElementById('selectAllStudents');
    const studentCheckboxes = document.querySelectorAll('.student-checkbox');

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            selectedStudentIds.clear(); // Clear existing selections
            studentCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
                if (this.checked) {
                    selectedStudentIds.add(parseInt(checkbox.dataset.id));
                }
            });
            updateDeleteSelectedButtonState();
        });
    }

    studentCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const studentId = parseInt(this.dataset.id);
            if (this.checked) {
                selectedStudentIds.add(studentId);
            } else {
                selectedStudentIds.delete(studentId);
            }
            // If any individual checkbox is unchecked, uncheck the "select all"
            if (!this.checked && selectAllCheckbox) {
                selectAllCheckbox.checked = false;
            }
            // If all individual checkboxes are checked, check the "select all"
            if (selectAllCheckbox && selectedStudentIds.size === studentCheckboxes.length) {
                selectAllCheckbox.checked = true;
            }
            updateDeleteSelectedButtonState();
        });
    });

    // Initial state of the delete selected button
    updateDeleteSelectedButtonState();
});

function updateDeleteSelectedButtonState() {
    const deleteSelectedBtn = document.querySelector('.delete-selected-btn');
    if (deleteSelectedBtn) {
        deleteSelectedBtn.disabled = selectedStudentIds.size === 0;
        deleteSelectedBtn.style.opacity = selectedStudentIds.size === 0 ? '0.5' : '1';
        deleteSelectedBtn.style.cursor = selectedStudentIds.size === 0 ? 'not-allowed' : 'pointer';
    }
}


function deleteSelectedStudents() {
    if (selectedStudentIds.size === 0) {
        showNotification('No students selected for deletion.', true);
        return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedStudentIds.size} selected students?`)) {
        return;
    }

    fetch(`/delete-multiple/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/json' // Send data as JSON
        },
        body: JSON.stringify({ ids: Array.from(selectedStudentIds) }) // Convert Set to Array for JSON
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showNotification('Selected students deleted successfully!');
            selectedStudentIds.clear(); // Clear selection
            location.reload(); // Reload page to reflect changes
        } else {
            showNotification(data.message || 'Failed to delete selected students.', true);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('An error occurred during bulk deletion.', true);
    });
}

// Function `inlineEdit` from previous solution is no longer needed if you removed inline-editing from home.html
// However, the `InlineEditView` in views.py and its corresponding URL can remain if you wish,
// they just won't be called from this home.html anymore.