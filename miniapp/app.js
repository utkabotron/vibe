/**
 * VIBE Mini App - Main Application
 */

// === Configuration ===
const API_BASE = '/api/miniapp';

// === State ===
const state = {
    user: null,
    references: null,
    currentDraft: null,
    selectedHours: null,
    selectedMinutes: null,
    currentCategory: 'labour',
    isOnline: navigator.onLine,
    reportsSentThisSession: 0,
    lastProjectId: null,
    lastProductId: null,
    // Selected material data (for getting unit)
    selectedPaintMaterial: null,
    selectedMaterial: null,
    // Screen management
    currentScreen: 'project' // 'project' | 'product' | 'report'
};

// === DOM Elements ===
const elements = {
    loading: null,
    toast: null,
    projectSelect: null,
    productSelect: null,
    actionsList: null,
    actionsCount: null,
    addActionBtn: null,
    actionForm: null,
    categoryTabs: null,
    labourTypeSelect: null,
    paintTypeSelect: null,
    paintMaterialSelect: null,
    paintQuantity: null,
    materialTypeSelect: null,
    materialSelect: null,
    materialQuantity: null,
    timeValue: null,
    hoursButtons: null,
    minutesButtons: null,
    comment: null,
    pendingIndicator: null,
    pendingCount: null,
    cancelActionBtn: null,
    confirmActionBtn: null,
    submitBtn: null,
    submitSection: null
};

// === Initialization ===
document.addEventListener('DOMContentLoaded', async () => {
    // Cache DOM elements
    cacheElements();

    // Initialize Telegram WebApp
    initTelegram();

    // Initialize database
    await vibeDB.init();

    // Load data
    await loadData();

    // Setup event listeners
    setupEventListeners();

    // Check for pending reports
    await checkPendingReports();

    // Hide loading
    hideLoading();
});

function cacheElements() {
    elements.loading = document.getElementById('loading');
    elements.toast = document.getElementById('toast');
    elements.projectSelect = document.getElementById('project-select');
    elements.productSelect = document.getElementById('product-select');
    elements.actionsList = document.getElementById('actions-list');
    elements.actionsCount = document.getElementById('actions-count');
    elements.addActionBtn = document.getElementById('add-action-btn');
    elements.actionForm = document.getElementById('action-form');
    elements.labourTypeSelect = document.getElementById('labour-type-select');
    elements.paintTypeSelect = document.getElementById('paint-type-select');
    elements.paintMaterialSelect = document.getElementById('paint-material-select');
    elements.paintQuantity = document.getElementById('paint-quantity');
    elements.materialTypeSelect = document.getElementById('material-type-select');
    elements.materialSelect = document.getElementById('material-select');
    elements.materialQuantity = document.getElementById('material-quantity');
    elements.timeValue = document.getElementById('time-value');
    elements.hoursButtons = document.querySelectorAll('.time-buttons.hours button');
    elements.minutesButtons = document.querySelectorAll('.time-buttons.minutes button');
    elements.comment = document.getElementById('comment');
    elements.pendingIndicator = document.getElementById('pending-indicator');
    elements.pendingCount = document.getElementById('pending-count');
    elements.cancelActionBtn = document.getElementById('cancel-action-btn');
    elements.confirmActionBtn = document.getElementById('confirm-action-btn');
    elements.categoryTabs = document.querySelectorAll('.category-tabs .tab');
    elements.submitBtn = document.getElementById('submit-btn');
    elements.submitSection = document.getElementById('submit-section');

    // Inject SVG icons
    injectIcons();
}

function injectIcons() {
    document.querySelectorAll('[data-icon]').forEach(el => {
        const iconName = el.dataset.icon;
        el.innerHTML = getIcon(iconName);
    });
}

function initTelegram() {
    if (window.Telegram?.WebApp) {
        const tg = window.Telegram.WebApp;

        // Expand to full height
        tg.expand();

        // Setup main button
        tg.MainButton.setText('Отправить отчёт');
        tg.MainButton.onClick(submitReport);

        // Enable closing confirmation
        tg.enableClosingConfirmation();

        // Get user data
        if (tg.initDataUnsafe?.user) {
            state.user = tg.initDataUnsafe.user;
        }

        // Theme
        document.body.style.backgroundColor = tg.backgroundColor;
    }
}

// === Data Loading ===
async function loadData() {
    try {
        // Try to load from cache first
        const cachedRefs = await vibeDB.getReferences();

        if (cachedRefs) {
            state.references = cachedRefs;
            populateSelects();
        }

        // Fetch fresh data from server
        if (state.isOnline) {
            await fetchReferences();
        } else if (!cachedRefs) {
            showToast('Нет подключения к сети', 'error');
        }

        // Load or create current draft
        await loadCurrentDraft();

    } catch (error) {
        console.error('Error loading data:', error);
        showToast('Ошибка загрузки данных', 'error');
    }
}

async function fetchReferences() {
    try {
        const initData = window.Telegram?.WebApp?.initData || '';

        const response = await fetch(`${API_BASE}/init`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ initData })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch references');
        }

        const data = await response.json();

        if (data.user) {
            state.user = { ...state.user, ...data.user };

            // Check if user is registered and active
            if (!data.user.is_registered) {
                showNotRegisteredMessage();
                return;
            }

            if (!data.user.is_active) {
                showInactiveMessage();
                return;
            }
        }

        if (data.references) {
            state.references = data.references;
            await vibeDB.saveReferences(data.references);
            populateSelects();
        }

    } catch (error) {
        console.error('Error fetching references:', error);
        // Don't show error if we have cached data
        if (!state.references) {
            showToast('Ошибка загрузки справочников', 'error');
        }
    }
}

function showNotRegisteredMessage() {
    document.getElementById('app').innerHTML = `
        <div class="error-screen">
            <div class="error-icon">🔒</div>
            <h2>Доступ ограничен</h2>
            <p>Вы не зарегистрированы в системе.</p>
            <p>Используйте бота для регистрации: отправьте команду /start</p>
        </div>
    `;
    hideLoading();
}

function showInactiveMessage() {
    document.getElementById('app').innerHTML = `
        <div class="error-screen">
            <div class="error-icon">⏸️</div>
            <h2>Аккаунт деактивирован</h2>
            <p>Ваш аккаунт временно деактивирован.</p>
            <p>Обратитесь к администратору.</p>
        </div>
    `;
    hideLoading();
}

async function loadCurrentDraft() {
    let draft = await vibeDB.getCurrentDraft();

    if (!draft) {
        draft = await vibeDB.createDraft({});
    }

    state.currentDraft = draft;
    renderDraft();
}

// === Populate Selects ===
function populateSelects() {
    if (!state.references) return;

    // Render project cards
    renderProjectCards();

    // Labour types
    const labourTypes = state.references.labourTypes || [];
    populateSelect(elements.labourTypeSelect, labourTypes, 'work_id', 'work_name', 'Выберите вид работы');

    // Paint types
    const paintTypes = state.references.paintTypes || [];
    populateSelect(elements.paintTypeSelect, paintTypes, 'type_id', 'type_name', 'Выберите тип ЛКМ');

    // Material types
    const materialTypes = state.references.materialTypes || [];
    populateSelect(elements.materialTypeSelect, materialTypes, 'type_id', 'type_name', 'Выберите тип материала');
}

function populateSelect(select, items, valueKey, textKey, placeholder) {
    select.innerHTML = `<option value="">${placeholder}</option>`;

    items.forEach(item => {
        // Handle flexible field names
        const value = item[valueKey] || item.id || item.type_id || item.work_id;
        const text = item[textKey] || item.name || item.type_name || item.work_name;

        const option = document.createElement('option');
        option.value = value;
        option.textContent = text;
        select.appendChild(option);
    });

    select.disabled = items.length === 0;
}

// === Event Listeners ===
function setupEventListeners() {
    // Paint type change
    elements.paintTypeSelect.addEventListener('change', onPaintTypeChange);

    // Material type change
    elements.materialTypeSelect.addEventListener('change', onMaterialTypeChange);

    // Add action button - now shows modal
    elements.addActionBtn.addEventListener('click', showCategorySelection);

    // Cancel action
    elements.cancelActionBtn.addEventListener('click', hideActionForm);

    // Confirm action
    elements.confirmActionBtn.addEventListener('click', addAction);

    // Category tabs
    elements.categoryTabs.forEach(tab => {
        tab.addEventListener('click', () => switchCategory(tab.dataset.category));
    });

    // Time buttons - Hours
    elements.hoursButtons.forEach(btn => {
        btn.addEventListener('click', () => selectTime('hours', btn));
    });

    // Time buttons - Minutes
    elements.minutesButtons.forEach(btn => {
        btn.addEventListener('click', () => selectTime('minutes', btn));
    });

    // Comment change
    elements.comment.addEventListener('input', onCommentChange);

    // Online/offline
    window.addEventListener('online', () => {
        state.isOnline = true;
        syncPendingReports();
    });

    window.addEventListener('offline', () => {
        state.isOnline = false;
    });

    // Submit button (for browser testing)
    if (elements.submitBtn) {
        elements.submitBtn.addEventListener('click', submitReport);
    }
}

// === Paint/Material Type Handling ===
async function onPaintTypeChange() {
    const typeId = elements.paintTypeSelect.value;

    elements.paintMaterialSelect.innerHTML = '<option value="">Загрузка...</option>';
    elements.paintMaterialSelect.disabled = true;
    state.selectedPaintMaterial = null;

    if (!typeId) {
        elements.paintMaterialSelect.innerHTML = '<option value="">Сначала выберите тип</option>';
        return;
    }

    const materials = state.references.paintMaterials?.[typeId] || [];
    populateSelect(elements.paintMaterialSelect, materials, 'material_id', 'material_name', 'Выберите материал');

    // Add change listener to track selected material
    elements.paintMaterialSelect.onchange = () => {
        const materialId = elements.paintMaterialSelect.value;
        state.selectedPaintMaterial = materials.find(m =>
            (m.material_id || m.id) === materialId
        ) || null;
    };
}

async function onMaterialTypeChange() {
    const typeId = elements.materialTypeSelect.value;

    elements.materialSelect.innerHTML = '<option value="">Загрузка...</option>';
    elements.materialSelect.disabled = true;
    state.selectedMaterial = null;

    if (!typeId) {
        elements.materialSelect.innerHTML = '<option value="">Сначала выберите тип</option>';
        return;
    }

    const materials = state.references.materials?.[typeId] || [];
    populateSelect(elements.materialSelect, materials, 'material_id', 'material_name', 'Выберите материал');

    // Add change listener to track selected material
    elements.materialSelect.onchange = () => {
        const materialId = elements.materialSelect.value;
        state.selectedMaterial = materials.find(m =>
            (m.material_id || m.id) === materialId
        ) || null;
    };
}

// === Comment Handling ===
async function onCommentChange() {
    await updateDraft({ comment: elements.comment.value });
}

// === Time Selection ===
function selectTime(type, btn) {
    const value = parseInt(btn.dataset.value);
    const buttons = type === 'hours' ? elements.hoursButtons : elements.minutesButtons;

    // Toggle selection
    if (btn.classList.contains('selected')) {
        btn.classList.remove('selected');
        if (type === 'hours') {
            state.selectedHours = null;
        } else {
            state.selectedMinutes = null;
        }
    } else {
        // Deselect others in group
        buttons.forEach(b => b.classList.remove('selected'));
        btn.classList.add('selected');

        if (type === 'hours') {
            state.selectedHours = value;
        } else {
            state.selectedMinutes = value;
        }
    }

    updateTimeDisplay();
    updateTimeLargeDisplay();

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }
}

function updateTimeDisplay() {
    const hours = state.selectedHours;
    const minutes = state.selectedMinutes;

    let display = '—';

    if (hours && minutes) {
        display = `${hours}ч ${minutes}м`;
    } else if (hours) {
        display = `${hours}ч`;
    } else if (minutes) {
        display = `${minutes}м`;
    }

    if (elements.timeValue) {
        elements.timeValue.textContent = display;
    }
}

function updateTimeLargeDisplay() {
    const hoursEl = document.getElementById('time-value-hours');
    const minutesEl = document.getElementById('time-value-minutes');

    if (!hoursEl || !minutesEl) return;

    const hours = state.selectedHours;
    const minutes = state.selectedMinutes;

    if (hours !== null) {
        hoursEl.textContent = String(hours).padStart(2, '0');
        hoursEl.classList.add('has-value');
    } else {
        hoursEl.textContent = '—';
        hoursEl.classList.remove('has-value');
    }

    if (minutes !== null) {
        minutesEl.textContent = String(minutes).padStart(2, '0');
        minutesEl.classList.add('has-value');
    } else {
        minutesEl.textContent = '—';
        minutesEl.classList.remove('has-value');
    }
}

function resetTimeSelection() {
    state.selectedHours = null;
    state.selectedMinutes = null;
    elements.hoursButtons.forEach(b => b.classList.remove('selected'));
    elements.minutesButtons.forEach(b => b.classList.remove('selected'));
    updateTimeDisplay();
    updateTimeLargeDisplay();
}

// === Category Switching ===
function switchCategory(category) {
    state.currentCategory = category;

    // Update tabs
    elements.categoryTabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.category === category);
    });

    // Update form content
    document.querySelectorAll('.form-content').forEach(form => {
        form.classList.remove('active');
    });
    document.getElementById(`form-${category}`).classList.add('active');

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }
}

// === Action Form ===
function showActionForm() {
    elements.addActionBtn.classList.add('hidden');
    elements.actionForm.classList.remove('hidden');
    resetActionForm();
}

function hideActionForm() {
    elements.actionForm.classList.add('hidden');
    elements.addActionBtn.classList.remove('hidden');
    resetActionForm();
}

function resetActionForm() {
    // Reset category to labour
    switchCategory('labour');

    // Reset time
    resetTimeSelection();

    // Reset selects
    elements.labourTypeSelect.value = '';
    elements.paintTypeSelect.value = '';
    elements.paintMaterialSelect.innerHTML = '<option value="">Сначала выберите тип</option>';
    elements.paintMaterialSelect.disabled = true;
    elements.paintQuantity.value = '';
    elements.materialTypeSelect.value = '';
    elements.materialSelect.innerHTML = '<option value="">Сначала выберите тип</option>';
    elements.materialSelect.disabled = true;
    elements.materialQuantity.value = '';
}

// === Add Action ===
async function addAction() {
    const action = buildCurrentAction();

    if (!action) {
        showToast('Заполните все поля', 'error');
        return;
    }

    // Add to draft
    const actions = [...(state.currentDraft.actions || []), action];
    await updateDraft({ actions });

    // Render
    renderActions();
    hideActionForm();
    updateMainButton();

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
    }

    showToast('Действие добавлено', 'success');
}

function buildCurrentAction() {
    const category = state.currentCategory;

    switch (category) {
        case 'labour': {
            const select = elements.labourTypeSelect;
            const typeId = select.value;
            if (!typeId) return null;

            const hours = state.selectedHours || 0;
            const minutes = state.selectedMinutes || 0;
            if (hours === 0 && minutes === 0) return null;

            const typeName = select.options[select.selectedIndex].text;
            const totalHours = hours + minutes / 60;

            return {
                category: 'Работы',
                subcategory: typeId,
                subcategory_name: typeName,
                type_name: 'Трудозатраты',
                quantity: String(totalHours),
                unit: 'ч.',
                displayTime: formatTime(hours, minutes)
            };
        }

        case 'paint': {
            const typeSelect = elements.paintTypeSelect;
            const materialSelect = elements.paintMaterialSelect;
            const quantity = parseFloat(elements.paintQuantity.value);

            if (!typeSelect.value || !materialSelect.value || isNaN(quantity) || quantity <= 0) {
                return null;
            }

            const typeName = typeSelect.options[typeSelect.selectedIndex].text;
            const materialName = materialSelect.options[materialSelect.selectedIndex].text;
            const unit = state.selectedPaintMaterial?.unit || 'л';

            return {
                category: 'ЛКМ',
                subcategory: materialSelect.value,
                subcategory_name: materialName,
                type_name: typeName,
                quantity: quantity.toString(),
                unit: unit
            };
        }

        case 'materials': {
            const typeSelect = elements.materialTypeSelect;
            const materialSelect = elements.materialSelect;
            const quantity = parseFloat(elements.materialQuantity.value);

            if (!typeSelect.value || !materialSelect.value || isNaN(quantity) || quantity <= 0) {
                return null;
            }

            const typeName = typeSelect.options[typeSelect.selectedIndex].text;
            const materialName = materialSelect.options[materialSelect.selectedIndex].text;
            const unit = state.selectedMaterial?.unit || '';

            return {
                category: 'Плита',
                subcategory: materialSelect.value,
                subcategory_name: materialName,
                type_name: typeName,
                quantity: quantity.toString(),
                unit: unit
            };
        }

        case 'defect': {
            return {
                category: 'Брак',
                subcategory: 'defect',
                subcategory_name: 'Брак',
                type_name: 'Брак',
                quantity: '',
                unit: ''
            };
        }

        default:
            return null;
    }
}

function formatTime(hours, minutes) {
    if (hours && minutes) {
        return `${hours}ч ${minutes}м`;
    } else if (hours) {
        return `${hours}ч`;
    } else if (minutes) {
        return `${minutes}м`;
    }
    return '—';
}

// === Delete Action ===
async function deleteAction(index) {
    const actions = [...(state.currentDraft.actions || [])];
    actions.splice(index, 1);
    await updateDraft({ actions });
    renderActions();
    updateMainButton();

    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('warning');
    }
}

// === Render ===
function renderDraft() {
    if (!state.currentDraft) return;

    // Comment
    elements.comment.value = state.currentDraft.comment || '';

    // Actions
    renderActions();

    // Project/Product display
    updateProjectDisplay();
    updateMainButton();
}

function renderActions() {
    const actions = state.currentDraft?.actions || [];

    elements.actionsCount.textContent = actions.length > 0 ? `(${actions.length})` : '';

    if (actions.length === 0) {
        elements.actionsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">${getIcon('plus')}</div>
                <p class="empty-text">Нет добавленных действий</p>
            </div>
        `;
        return;
    }

    elements.actionsList.innerHTML = actions.map((action, index) => {
        const categoryKey = getCategoryKey(action.category);
        const icon = getIcon(categoryKey);
        const subtitle = action.displayTime || `${action.quantity} ${action.unit}`;

        return `
            <div class="action-card">
                <div class="action-icon" data-category="${categoryKey}">
                    ${icon}
                </div>
                <div class="action-content">
                    <p class="action-title">${action.subcategory_name}</p>
                    <p class="action-value">${subtitle}</p>
                </div>
                <button class="action-delete" onclick="deleteAction(${index})" aria-label="Удалить">
                    ${getIcon('close')}
                </button>
            </div>
        `;
    }).join('');
}

function getCategoryKey(category) {
    const map = {
        'Работы': 'labour',
        'ЛКМ': 'paint',
        'Плита': 'materials',
        'Брак': 'defect'
    };
    return map[category] || 'labour';
}

// === Draft Management ===
async function updateDraft(updates) {
    if (!state.currentDraft) return;

    state.currentDraft = await vibeDB.updateDraft(state.currentDraft.id, updates);
}

// === Main Button ===
function updateMainButton() {
    const tg = window.Telegram?.WebApp;
    const draft = state.currentDraft;
    const isValid = draft?.projectId &&
        draft?.productId &&
        draft?.actions?.length > 0;

    // Telegram MainButton
    if (tg) {
        if (isValid) {
            tg.MainButton.show();
            tg.MainButton.enable();
        } else {
            tg.MainButton.hide();
        }
    }

    // HTML Submit Button (for browser testing)
    if (elements.submitBtn) {
        elements.submitBtn.disabled = !isValid;
    }
}

// === Submit Report ===
async function submitReport() {
    const tg = window.Telegram?.WebApp;
    const draft = state.currentDraft;

    if (!draft || !draft.actions?.length) {
        showToast('Добавьте хотя бы одно действие', 'error');
        return;
    }

    // Disable buttons
    if (tg) {
        tg.MainButton.showProgress();
        tg.MainButton.disable();
    }
    if (elements.submitBtn) {
        elements.submitBtn.disabled = true;
        elements.submitBtn.textContent = 'Отправка...';
    }

    try {
        // Prepare report data (use employee data from Users table)
        const report = {
            timestamp: new Date().toISOString(),
            employee_id: String(state.user?.employee_id || state.user?.telegram_id || ''),
            employee_name: state.user?.employee_name || state.user?.telegram_name || 'Unknown',
            project_id: draft.projectId,
            project_name: draft.projectName,
            product_id: draft.productId,
            product_name: draft.productName,
            actions: draft.actions,
            comment: draft.comment || ''
        };

        if (state.isOnline) {
            // Try to submit
            const success = await sendReport(report);

            if (success) {
                // Mark as synced
                await vibeDB.markAsSynced(draft.id);

                // Remember last project/product for convenience
                state.lastProjectId = draft.projectId;
                state.lastProductId = draft.productId;

                // Create new draft with same project/product
                const newDraft = await vibeDB.createDraft({
                    projectId: draft.projectId,
                    projectName: draft.projectName,
                    productId: draft.productId,
                    productName: draft.productName
                });
                state.currentDraft = newDraft;
                renderDraft();

                // Haptic
                if (tg?.HapticFeedback) {
                    tg.HapticFeedback.notificationOccurred('success');
                }

                // Increment sent counter
                state.reportsSentThisSession = (state.reportsSentThisSession || 0) + 1;
                updateSentCounter();

                showToast(`Отчёт #${state.reportsSentThisSession} отправлен!`, 'success');

                // Don't close - allow creating more reports

            } else {
                throw new Error('Failed to submit');
            }
        } else {
            // Save as pending
            await vibeDB.markAsPending(draft.id);

            // Remember last project/product
            state.lastProjectId = draft.projectId;
            state.lastProductId = draft.productId;

            // Create new draft with same project/product
            const newDraft = await vibeDB.createDraft({
                projectId: draft.projectId,
                projectName: draft.projectName,
                productId: draft.productId,
                productName: draft.productName
            });
            state.currentDraft = newDraft;
            renderDraft();

            // Increment counter (pending also counts)
            state.reportsSentThisSession = (state.reportsSentThisSession || 0) + 1;
            updateSentCounter();

            showToast(`Отчёт #${state.reportsSentThisSession} сохранён. Отправится при подключении`, 'success');
            await checkPendingReports();
        }

    } catch (error) {
        console.error('Submit error:', error);
        showToast('Ошибка отправки. Сохранено локально.', 'error');

        // Save as pending
        await vibeDB.markAsPending(draft.id);
        await checkPendingReports();

    } finally {
        if (tg) {
            tg.MainButton.hideProgress();
        }
        if (elements.submitBtn) {
            elements.submitBtn.textContent = 'Отправить в таблицу';
        }
        updateMainButton();
    }
}

async function sendReport(report) {
    const initData = window.Telegram?.WebApp?.initData || '';

    const response = await fetch(`${API_BASE}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initData, report })
    });

    return response.ok;
}

// === Pending Reports ===
async function checkPendingReports() {
    const count = await vibeDB.getPendingCount();

    if (count > 0) {
        elements.pendingCount.textContent = count;
        elements.pendingIndicator.classList.remove('hidden');
    } else {
        elements.pendingIndicator.classList.add('hidden');
    }
}

async function syncPendingReports() {
    const pending = await vibeDB.getPendingReports();

    for (const report of pending) {
        try {
            const reportData = {
                timestamp: new Date(report.createdAt).toISOString(),
                employee_id: String(state.user?.id || ''),
                employee_name: state.user?.first_name || 'Unknown',
                project_id: report.projectId,
                project_name: report.projectName,
                product_id: report.productId,
                product_name: report.productName,
                actions: report.actions,
                comment: report.comment || ''
            };

            const success = await sendReport(reportData);

            if (success) {
                await vibeDB.markAsSynced(report.id);
            } else {
                await vibeDB.incrementRetry(report.id);
            }
        } catch (error) {
            console.error('Sync error:', error);
            await vibeDB.incrementRetry(report.id);
        }
    }

    await checkPendingReports();
}

// === UI Helpers ===
function showLoading() {
    elements.loading.classList.remove('hidden');
}

function hideLoading() {
    elements.loading.classList.add('hidden');
}

function showToast(message, type = 'info') {
    elements.toast.textContent = message;
    elements.toast.className = `toast ${type}`;

    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 3000);
}

// === Sent Counter ===
function updateSentCounter() {
    const counter = document.getElementById('sent-counter');
    if (counter) {
        if (state.reportsSentThisSession > 0) {
            counter.textContent = `Отправлено: ${state.reportsSentThisSession}`;
            counter.classList.remove('hidden');
        } else {
            counter.classList.add('hidden');
        }
    }
}

// === Modal Management ===
function showCategorySelection() {
    const modal = document.getElementById('category-modal');
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
}

function selectCategory(category) {
    // Close category modal
    document.getElementById('category-modal').classList.add('hidden');

    // Show action form modal
    showActionFormModal(category);
}

function showActionFormModal(category) {
    const modal = document.getElementById('action-modal');
    const title = document.getElementById('modal-title');
    const container = document.getElementById('dynamic-form-container');

    // Set category
    state.currentCategory = category;

    // Update title
    const categoryNames = {
        'labour': 'Работы',
        'paint': 'ЛКМ',
        'materials': 'Плита',
        'defect': 'Брак'
    };
    title.textContent = categoryNames[category] || 'Действие';

    // Load form template
    container.innerHTML = getFormTemplate(category);

    // Reinitialize form elements
    reinitializeFormElements();

    // Show modal
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
}

function getFormTemplate(category) {
    switch (category) {
        case 'labour':
            return `
                <div class="field">
                    <label>Вид работы</label>
                    <div class="select-wrapper">
                        <select id="modal-labour-type">
                            <option value="">Выберите</option>
                        </select>
                        <span class="select-icon" data-icon="chevronDown"></span>
                    </div>
                </div>
                <div id="modal-time-picker"></div>
            `;
        case 'paint':
            return `
                <div class="field">
                    <label>Тип ЛКМ</label>
                    <div class="select-wrapper">
                        <select id="modal-paint-type">
                            <option value="">Выберите</option>
                        </select>
                        <span class="select-icon" data-icon="chevronDown"></span>
                    </div>
                </div>
                <div class="field">
                    <label>Материал</label>
                    <div class="select-wrapper">
                        <select id="modal-paint-material" disabled>
                            <option value="">Сначала выберите тип</option>
                        </select>
                        <span class="select-icon" data-icon="chevronDown"></span>
                    </div>
                </div>
                <div class="field">
                    <label>Количество (л)</label>
                    <input type="number" id="modal-paint-quantity" step="0.1" min="0" placeholder="0.0">
                </div>
            `;
        case 'materials':
            return `
                <div class="field">
                    <label>Тип материала</label>
                    <div class="select-wrapper">
                        <select id="modal-material-type">
                            <option value="">Выберите</option>
                        </select>
                        <span class="select-icon" data-icon="chevronDown"></span>
                    </div>
                </div>
                <div class="field">
                    <label>Материал</label>
                    <div class="select-wrapper">
                        <select id="modal-material" disabled>
                            <option value="">Сначала выберите тип</option>
                        </select>
                        <span class="select-icon" data-icon="chevronDown"></span>
                    </div>
                </div>
                <div class="field">
                    <label>Количество</label>
                    <input type="number" id="modal-material-quantity" step="0.1" min="0" placeholder="0.0">
                </div>
            `;
        case 'defect':
            return `<p class="hint">Брак будет добавлен с комментарием</p>`;
        default:
            return '';
    }
}

function reinitializeFormElements() {
    // Inject icons
    injectIcons();

    // Populate selects based on category
    if (state.currentCategory === 'labour') {
        const select = document.getElementById('modal-labour-type');
        if (select) {
            populateSelect(select, state.references?.labourTypes || [], 'work_id', 'work_name', 'Выберите вид работы');
        }
        // Add simplified time picker
        const timePickerContainer = document.getElementById('modal-time-picker');
        if (timePickerContainer) {
            timePickerContainer.innerHTML = `
                <div class="time-picker-simple">
                    <label>Время работы</label>

                    <div class="preset-grid">
                        <button class="preset-btn" data-minutes="15">15м</button>
                        <button class="preset-btn" data-minutes="30">30м</button>
                        <button class="preset-btn" data-minutes="60">1ч</button>
                        <button class="preset-btn" data-minutes="120">2ч</button>
                        <button class="preset-btn" data-minutes="240">4ч</button>
                        <button class="preset-btn" data-minutes="480">8ч</button>
                    </div>

                    <div class="time-display-simple">
                        Выбрано: <strong id="time-display-value">—</strong>
                    </div>

                    <div class="stepper-controls">
                        <button class="stepper-btn minus" onclick="adjustTime(-15)">
                            <span>−</span> 15м
                        </button>
                        <button class="stepper-btn plus" onclick="adjustTime(15)">
                            <span>+</span> 15м
                        </button>
                    </div>
                </div>
            `;

            // Add event listeners to preset buttons
            document.querySelectorAll('.preset-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const minutes = parseInt(this.dataset.minutes);
                    selectTimePreset(minutes);
                });
            });
        }
    } else if (state.currentCategory === 'paint') {
        const typeSelect = document.getElementById('modal-paint-type');
        if (typeSelect) {
            populateSelect(typeSelect, state.references?.paintTypes || [], 'type_id', 'type_name', 'Выберите тип ЛКМ');
            typeSelect.onchange = () => {
                const typeId = typeSelect.value;
                const materialSelect = document.getElementById('modal-paint-material');
                if (materialSelect) {
                    const materials = state.references.paintMaterials?.[typeId] || [];
                    populateSelect(materialSelect, materials, 'material_id', 'material_name', 'Выберите материал');
                    materialSelect.onchange = () => {
                        const materialId = materialSelect.value;
                        state.selectedPaintMaterial = materials.find(m => (m.material_id || m.id) === materialId) || null;
                    };
                }
            };
        }
    } else if (state.currentCategory === 'materials') {
        const typeSelect = document.getElementById('modal-material-type');
        if (typeSelect) {
            populateSelect(typeSelect, state.references?.materialTypes || [], 'type_id', 'type_name', 'Выберите тип материала');
            typeSelect.onchange = () => {
                const typeId = typeSelect.value;
                const materialSelect = document.getElementById('modal-material');
                if (materialSelect) {
                    const materials = state.references.materials?.[typeId] || [];
                    populateSelect(materialSelect, materials, 'material_id', 'material_name', 'Выберите материал');
                    materialSelect.onchange = () => {
                        const materialId = materialSelect.value;
                        state.selectedMaterial = materials.find(m => (m.material_id || m.id) === materialId) || null;
                    };
                }
            };
        }
    }
}

function closeModal() {
    document.querySelectorAll('.modal').forEach(m => m.classList.add('hidden'));
    document.body.style.overflow = '';

    // Reset form state
    resetActionForm();
    resetSimpleTimePicker();

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
}

function backToCategories() {
    closeModal();
    setTimeout(() => showCategorySelection(), 100);
}

async function addActionFromModal() {
    const action = buildCurrentActionFromModal();

    if (!action) {
        showToast('Заполните все поля', 'error');
        return;
    }

    // Add to draft
    const actions = [...(state.currentDraft.actions || []), action];
    await updateDraft({ actions });

    // Render
    renderActions();
    closeModal();
    updateMainButton();

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
    }

    showToast('Действие добавлено', 'success');
}

function buildCurrentActionFromModal() {
    const category = state.currentCategory;

    switch (category) {
        case 'labour': {
            const select = document.getElementById('modal-labour-type');
            const typeId = select?.value;
            if (!typeId) return null;

            const hours = state.selectedHours || 0;
            const minutes = state.selectedMinutes || 0;
            if (hours === 0 && minutes === 0) return null;

            const typeName = select.options[select.selectedIndex].text;
            const totalHours = hours + minutes / 60;

            return {
                category: 'Работы',
                subcategory: typeId,
                subcategory_name: typeName,
                type_name: 'Трудозатраты',
                quantity: String(totalHours),
                unit: 'ч.',
                displayTime: formatTime(hours, minutes)
            };
        }

        case 'paint': {
            const materialSelect = document.getElementById('modal-paint-material');
            const quantity = parseFloat(document.getElementById('modal-paint-quantity')?.value);
            const typeSelect = document.getElementById('modal-paint-type');

            if (!materialSelect?.value || isNaN(quantity) || quantity <= 0) {
                return null;
            }

            const typeName = typeSelect.options[typeSelect.selectedIndex].text;
            const materialName = materialSelect.options[materialSelect.selectedIndex].text;
            const unit = state.selectedPaintMaterial?.unit || 'л';

            return {
                category: 'ЛКМ',
                subcategory: materialSelect.value,
                subcategory_name: materialName,
                type_name: typeName,
                quantity: quantity.toString(),
                unit: unit
            };
        }

        case 'materials': {
            const materialSelect = document.getElementById('modal-material');
            const quantity = parseFloat(document.getElementById('modal-material-quantity')?.value);
            const typeSelect = document.getElementById('modal-material-type');

            if (!materialSelect?.value || isNaN(quantity) || quantity <= 0) {
                return null;
            }

            const typeName = typeSelect.options[typeSelect.selectedIndex].text;
            const materialName = materialSelect.options[materialSelect.selectedIndex].text;
            const unit = state.selectedMaterial?.unit || '';

            return {
                category: 'Плита',
                subcategory: materialSelect.value,
                subcategory_name: materialName,
                type_name: typeName,
                quantity: quantity.toString(),
                unit: unit
            };
        }

        case 'defect': {
            return {
                category: 'Брак',
                subcategory: 'defect',
                subcategory_name: 'Брак',
                type_name: 'Брак',
                quantity: '',
                unit: ''
            };
        }

        default:
            return null;
    }
}

// === Simplified Time Picker ===
let selectedMinutes = 0;

function selectTimePreset(minutes) {
    selectedMinutes = minutes;

    // Update state (convert to hours and minutes)
    state.selectedHours = Math.floor(minutes / 60);
    state.selectedMinutes = minutes % 60;

    // Update UI
    document.querySelectorAll('.preset-btn').forEach(b =>
        b.classList.remove('selected')
    );
    const btn = document.querySelector(`[data-minutes="${minutes}"]`);
    if (btn) btn.classList.add('selected');

    updateSimpleTimeDisplay();

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }
}

function adjustTime(delta) {
    selectedMinutes = Math.max(0, selectedMinutes + delta);

    // Update state
    state.selectedHours = Math.floor(selectedMinutes / 60);
    state.selectedMinutes = selectedMinutes % 60;

    // Deselect presets
    document.querySelectorAll('.preset-btn').forEach(b =>
        b.classList.remove('selected')
    );

    updateSimpleTimeDisplay();

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.selectionChanged();
    }
}

function updateSimpleTimeDisplay() {
    const displayEl = document.getElementById('time-display-value');
    if (!displayEl) return;

    const hours = Math.floor(selectedMinutes / 60);
    const mins = selectedMinutes % 60;

    let display = '—';
    if (selectedMinutes > 0) {
        if (hours > 0 && mins > 0) {
            display = `${hours}ч ${mins}м`;
        } else if (hours > 0) {
            display = `${hours}ч`;
        } else {
            display = `${mins}м`;
        }
    }

    displayEl.textContent = display;
}

function resetSimpleTimePicker() {
    selectedMinutes = 0;
    state.selectedHours = null;
    state.selectedMinutes = null;
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('selected'));
    updateSimpleTimeDisplay();
}

// === Project Cards Rendering ===
function renderProjectCards() {
    const container = document.getElementById('project-cards-grid');
    if (!container) return;

    const projects = state.references?.projects || [];

    if (projects.length === 0) {
        container.innerHTML = '<p class="hint">Проекты не найдены</p>';
        return;
    }

    container.innerHTML = projects.map(project => {
        const projectId = String(project.project_id || project.id);
        const projectName = project.project_name || project.name;
        const isSelected = state.currentDraft?.projectId === projectId;

        return `
            <button class="project-card ${isSelected ? 'selected' : ''}"
                    data-project-id="${projectId}"
                    onclick="selectProject('${projectId}')">
                ${projectName}
            </button>
        `;
    }).join('');
}

function selectProject(projectId) {
    const project = state.references.projects.find(p =>
        String(p.project_id || p.id) === String(projectId)
    );

    if (!project) return;

    // Haptic feedback first (instant)
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('medium');
    }

    // Update state immediately for instant UI update
    state.currentDraft.projectId = projectId;
    state.currentDraft.projectName = project.project_name || project.name;
    state.currentDraft.productId = null;
    state.currentDraft.productName = null;

    // Go to product selection screen
    showScreen('product');
    renderProductCards(projectId);

    // Save to IndexedDB in background (async, non-blocking)
    updateDraft({
        projectId,
        projectName: project.project_name || project.name,
        productId: null,
        productName: null
    });
}

function renderProductCards(projectId) {
    const container = document.getElementById('product-cards-grid');
    if (!container) return;

    const products = state.references?.products?.[projectId] || [];

    if (products.length === 0) {
        container.innerHTML = '<p class="hint">Изделия не найдены</p>';
        return;
    }

    container.innerHTML = products.map(product => {
        const productId = String(product.product_id || product.id);
        const productName = product.product_name || product.name;
        const isSelected = state.currentDraft?.productId === productId;

        return `
            <button class="product-card ${isSelected ? 'selected' : ''}"
                    data-product-id="${productId}"
                    onclick="selectProduct('${productId}')">
                ${productName}
            </button>
        `;
    }).join('');
}

function selectProduct(productId) {
    const projectId = state.currentDraft?.projectId;
    if (!projectId) return;

    const products = state.references.products?.[projectId] || [];
    const product = products.find(p =>
        String(p.product_id || p.id) === String(productId)
    );

    if (!product) return;

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
    }

    // Update state immediately
    state.currentDraft.productId = productId;
    state.currentDraft.productName = product.product_name || product.name;

    // Go to report screen
    showScreen('report');
    updateProjectBadge();
    updateMainButton();

    // Save to IndexedDB in background
    updateDraft({
        productId,
        productName: product.product_name || product.name
    });
}

// === Screen Management ===
function showScreen(screenName) {
    state.currentScreen = screenName;

    // Hide all screens
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));

    // Show requested screen
    const screen = document.getElementById(`screen-${screenName}`);
    if (screen) {
        screen.classList.remove('hidden');
        window.scrollTo(0, 0);
    }
}

function goBackToProjects() {
    showScreen('project');
    renderProjectCards();

    // Haptic feedback
    if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.impactOccurred('light');
    }
}

function updateProjectBadge() {
    const draft = state.currentDraft;
    if (!draft?.projectId || !draft?.productId) return;

    document.getElementById('project-name-badge').textContent = draft.projectName || draft.projectId;
    document.getElementById('product-name-badge').textContent = draft.productName || draft.productId;
}

function editProjectProduct() {
    showScreen('project');
    renderProjectCards();
}

// === Project/Product Selection Modal (deprecated - keeping for compatibility) ===
function showProjectSelectionModal() {
    const modal = document.getElementById('action-modal');
    const title = document.getElementById('modal-title');
    const container = document.getElementById('dynamic-form-container');

    title.textContent = 'Выберите проект и изделие';

    container.innerHTML = `
        <div class="field">
            <label>Проект</label>
            <div class="select-wrapper">
                <select id="modal-project-select">
                    <option value="">Выберите проект</option>
                </select>
                <span class="select-icon" data-icon="chevronDown"></span>
            </div>
        </div>
        <div class="field">
            <label>Изделие</label>
            <div class="select-wrapper">
                <select id="modal-product-select" disabled>
                    <option value="">Сначала выберите проект</option>
                </select>
                <span class="select-icon" data-icon="chevronDown"></span>
            </div>
        </div>
    `;

    // Inject icons
    injectIcons();

    // Populate projects
    const projectSelect = document.getElementById('modal-project-select');
    const productSelect = document.getElementById('modal-product-select');

    if (projectSelect && state.references?.projects) {
        populateSelect(projectSelect, state.references.projects, 'project_id', 'project_name', 'Выберите проект');

        // Set current value if exists
        if (state.currentDraft?.projectId) {
            projectSelect.value = state.currentDraft.projectId;
        }

        projectSelect.onchange = async () => {
            const projectId = projectSelect.value;

            if (!projectId) {
                productSelect.innerHTML = '<option value="">Сначала выберите проект</option>';
                productSelect.disabled = true;
                return;
            }

            // Get project name
            const project = state.references.projects.find(p =>
                String(p.project_id || p.id) === String(projectId)
            );

            // Load products
            const products = state.references.products?.[projectId] || [];
            populateSelect(productSelect, products, 'product_id', 'product_name', 'Выберите изделие');

            // Set current value if exists and matches project
            if (state.currentDraft?.productId && state.currentDraft?.projectId === projectId) {
                productSelect.value = state.currentDraft.productId;
            }
        };

        // Trigger change if project is already selected
        if (state.currentDraft?.projectId) {
            projectSelect.dispatchEvent(new Event('change'));
        }
    }

    // Update modal footer button
    const modalBtn = document.getElementById('modal-add-btn');
    if (modalBtn) {
        modalBtn.textContent = 'Сохранить';
        modalBtn.onclick = async () => {
            const projectId = projectSelect?.value;
            const productId = productSelect?.value;

            if (!projectId || !productId) {
                showToast('Выберите проект и изделие', 'error');
                return;
            }

            // Get names
            const project = state.references.projects.find(p =>
                String(p.project_id || p.id) === String(projectId)
            );
            const products = state.references.products?.[projectId] || [];
            const product = products.find(p =>
                String(p.product_id || p.id) === String(productId)
            );

            // Update draft
            await updateDraft({
                projectId,
                projectName: project?.project_name || project?.name || projectId,
                productId,
                productName: product?.product_name || product?.name || productId
            });

            // Update hidden selects for compatibility
            elements.projectSelect.value = projectId;
            elements.productSelect.value = productId;

            closeModal();
            updateProjectDisplay();
            updateMainButton();

            showToast('Проект и изделие сохранены', 'success');
        };
    }

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function changeProject() {
    showProjectSelectionModal();
}

function updateProjectDisplay() {
    const draft = state.currentDraft;

    if (draft?.projectId && draft?.productId) {
        // Both selected - show report screen
        showScreen('report');
        updateProjectBadge();
    } else if (draft?.projectId) {
        // Only project selected - show product screen
        showScreen('product');
        renderProductCards(draft.projectId);
    } else {
        // Nothing selected - show project screen
        showScreen('project');
        renderProjectCards();
    }
}

// === Make functions global for onclick ===
window.deleteAction = deleteAction;
window.closeModal = closeModal;
window.backToCategories = backToCategories;
window.selectCategory = selectCategory;
window.addActionFromModal = addActionFromModal;
window.adjustTime = adjustTime;
window.showProjectSelectionModal = showProjectSelectionModal;
window.changeProject = changeProject;
window.selectProject = selectProject;
window.selectProduct = selectProduct;
window.editProjectProduct = editProjectProduct;
window.goBackToProjects = goBackToProjects;
