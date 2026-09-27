// API 基础地址
const API_BASE = '';

// 当前登录用户
let currentUser = null;

// 页面加载时初始化
window.addEventListener('load', function() {
    // 加载大模型配置
    loadLLMConfig();
});

// 分页状态
let paginationState = {
    page: 1,
    perPage: 10,
    total: 0
};

// CIO维护页面分页状态
let maintainPaginationState = {
    page: 1,
    perPage: 10,
    total: 0
};

// 选中的CIO记录ID
let selectedCioIds = new Set();

// 导入数据缓存
let importDataCache = [];

// ==================== 登录功能 ====================
document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const userCode = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch(`${API_BASE}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_code: userCode, password: password })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentUser = result.user;
            document.getElementById('currentUser').textContent = result.user.name;
            document.getElementById('loginPage').style.display = 'none';
            document.getElementById('mainPage').style.display = 'block';
            loadUsers();
        } else {
            showError(result.message);
        }
    } catch (error) {
        showError('登录失败，请检查网络连接');
    }
});

function showError(message) {
    const errorMsg = document.getElementById('errorMsg');
    errorMsg.textContent = message;
    errorMsg.style.display = 'block';
}

function logout() {
    currentUser = null;
    document.getElementById('loginPage').style.display = 'flex';
    document.getElementById('mainPage').style.display = 'none';
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
    document.getElementById('errorMsg').style.display = 'none';
}

// ==================== 页面切换 ====================
function showPage(pageId, menuItem) {
    // 隐藏所有页面
    document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
    document.querySelectorAll('.menu-item').forEach(item => item.classList.remove('active'));
    
    // 显示选中页面
    document.getElementById(pageId).classList.add('active');
    menuItem.classList.add('active');
    
    // 加载对应数据
    if (pageId === 'userPage') {
        loadUsers();
    } else if (pageId === 'cioQueryPage') {
        searchCio();
    } else if (pageId === 'cioMaintainPage') {
        searchCioForMaintain();
    }
}

// ==================== 用户管理 ====================
async function loadUsers() {
    try {
        const response = await fetch(`${API_BASE}/api/users`);
        const result = await response.json();
        
        if (result.success) {
            renderUserTable(result.data);
        }
    } catch (error) {
        console.error('加载用户失败:', error);
    }
}

function renderUserTable(users) {
    const tbody = document.getElementById('userTableBody');
    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.id}</td>
            <td>${user.user_code}</td>
            <td>${user.name}</td>
            <td>${user.created_at}</td>
            <td>
                <button class="action-btn edit-btn" onclick="editUser(${user.id}, '${user.user_code}', '${user.name}')">编辑</button>
                <button class="action-btn delete-btn" onclick="deleteUser(${user.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

function openUserModal() {
    document.getElementById('userModalTitle').textContent = '新增用户';
    document.getElementById('userForm').reset();
    document.getElementById('userId').value = '';
    document.getElementById('pwdHint').style.display = 'none';
    document.getElementById('userPassword').required = true;
    document.getElementById('userModal').classList.add('active');
}

function closeUserModal() {
    document.getElementById('userModal').classList.remove('active');
}

function editUser(id, userCode, name) {
    document.getElementById('userModalTitle').textContent = '编辑用户';
    document.getElementById('userId').value = id;
    document.getElementById('userCode').value = userCode;
    document.getElementById('userName').value = name;
    document.getElementById('userPassword').value = '';
    document.getElementById('pwdHint').style.display = 'inline';
    document.getElementById('userPassword').required = false;
    document.getElementById('userModal').classList.add('active');
}

document.getElementById('userForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const id = document.getElementById('userId').value;
    const data = {
        user_code: document.getElementById('userCode').value,
        name: document.getElementById('userName').value,
        password: document.getElementById('userPassword').value
    };
    
    try {
        const url = id ? `${API_BASE}/api/users/${id}` : `${API_BASE}/api/users`;
        const method = id ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeUserModal();
            loadUsers();
            alert(result.message);
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('操作失败，请重试');
    }
});

async function deleteUser(id) {
    if (!confirm('确定要删除该用户吗？')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/users/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            loadUsers();
            alert(result.message);
        }
    } catch (error) {
        alert('删除失败，请重试');
    }
}

// ==================== CIO整理（导入） ====================
// 使用大模型开关切换
document.getElementById('useLLM')?.addEventListener('change', function() {
    const info = document.getElementById('importMethodInfo');
    if (this.checked) {
        info.className = 'import-method-info llm';
        info.textContent = '将使用大模型智能识别文件中的姓名、单位、手机号等字段';
    } else {
        info.className = 'import-method-info traditional';
        info.textContent = '使用传统方式导入，需要文件列名与标准字段匹配';
    }
});

// 当前导入的文件名
let currentImportFileName = '';

// 显示进度条
function showProgress(percent, text) {
    const progressDiv = document.getElementById('importProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    progressDiv.style.display = 'block';
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

// 隐藏进度条
function hideProgress() {
    document.getElementById('importProgress').style.display = 'none';
}

// 显示导入成功提示
function showImportSuccess(fileName, count) {
    const successDiv = document.getElementById('importSuccess');
    const successText = document.getElementById('importSuccessText');
    
    successDiv.style.display = 'flex';
    successText.textContent = `文件 "${fileName}" 导入成功，共 ${count} 条数据`;
    
    // 3秒后自动隐藏
    setTimeout(() => {
        successDiv.style.display = 'none';
    }, 5000);
}

async function handleFileImport(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    currentImportFileName = file.name;
    
    // 显示进度条
    showProgress(10, '正在读取文件...');
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('use_llm', document.getElementById('useLLM')?.checked ? 'true' : 'false');
    
    try {
        showProgress(50, '正在解析数据...');
        
        const response = await fetch(`${API_BASE}/api/import`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            showProgress(100, '导入完成！');
            importDataCache = result.data;
            renderImportTable(importDataCache);
            
            // 显示成功提示
            showImportSuccess(file.name, result.count);
            
            // 隐藏进度条
            setTimeout(hideProgress, 1000);
        } else {
            hideProgress();
            alert(result.message);
        }
    } catch (error) {
        hideProgress();
        alert('文件导入失败，请检查文件格式');
    }
    
    // 清空文件输入，允许重复选择同一文件
    event.target.value = '';
}

function renderImportTable(data) {
    const tbody = document.getElementById('importTableBody');
    tbody.innerHTML = data.map((row, index) => `
        <tr data-index="${index}">
            <td><input type="text" value="${row.name || ''}" class="edit-name"></td>
            <td><input type="text" value="${row.unit_name || ''}" class="edit-unit"></td>
            <td><input type="text" value="${row.phone || ''}" class="edit-phone"></td>
            <td><input type="text" value="${row.email || ''}" class="edit-email"></td>
            <td><input type="text" value="${row.unit_full_name || ''}" class="edit-fullunit"></td>
            <td><input type="text" value="${row.position || ''}" class="edit-position"></td>
            <td><input type="text" value="${row.gender || ''}" class="edit-gender"></td>
            <td><input type="text" value="${row.home_address || ''}" class="edit-address"></td>
            <td>
                <button class="action-btn delete-btn" onclick="deleteImportRow(${index})">删除</button>
            </td>
        </tr>
    `).join('');
}

function addEmptyRow() {
    importDataCache.push({
        name: '',
        unit_name: '',
        phone: '',
        email: '',
        unit_full_name: '',
        position: '',
        gender: '',
        home_address: ''
    });
    renderImportTable(importDataCache);
}

function deleteImportRow(index) {
    importDataCache.splice(index, 1);
    renderImportTable(importDataCache);
}

function clearImportData() {
    if (importDataCache.length > 0 && !confirm('确定要清空所有数据吗？')) return;
    importDataCache = [];
    renderImportTable(importDataCache);
}

async function saveImportData() {
    if (importDataCache.length === 0) {
        alert('没有数据需要保存');
        return;
    }
    
    // 收集表格中的数据
    const rows = document.querySelectorAll('#importTableBody tr');
    const dataToSave = [];
    
    rows.forEach(row => {
        dataToSave.push({
            name: row.querySelector('.edit-name').value,
            unit_name: row.querySelector('.edit-unit').value,
            phone: row.querySelector('.edit-phone').value,
            email: row.querySelector('.edit-email').value,
            unit_full_name: row.querySelector('.edit-fullunit').value,
            position: row.querySelector('.edit-position').value,
            gender: row.querySelector('.edit-gender').value,
            home_address: row.querySelector('.edit-address').value
        });
    });
    
    // 检查是否启用了去重更新模式
    const upsertMode = document.getElementById('upsertMode')?.checked || false;
    
    try {
        const response = await fetch(`${API_BASE}/api/cio/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                data: dataToSave,
                upsert: upsertMode
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(result.message);
            importDataCache = [];
            renderImportTable(importDataCache);
            // 清空文件名
            currentImportFileName = '';
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('保存失败，请重试');
    }
}

// ==================== CIO查询 ====================
async function searchCio() {
    const params = new URLSearchParams({
        page: paginationState.page,
        per_page: paginationState.perPage,
        name: document.getElementById('searchName').value,
        unit_name: document.getElementById('searchUnit').value,
        phone: document.getElementById('searchPhone').value,
        unit_full_name: document.getElementById('searchFullUnit').value
    });
    
    try {
        const response = await fetch(`${API_BASE}/api/cio?${params}`);
        const result = await response.json();
        
        if (result.success) {
            renderCioTable(result.data);
            paginationState.total = result.total;
            renderPagination();
            
            // 显示总记录数
            const resultInfo = document.getElementById('queryResultInfo');
            const totalRecords = document.getElementById('totalRecords');
            resultInfo.style.display = 'block';
            totalRecords.textContent = result.total;
        }
    } catch (error) {
        console.error('查询失败:', error);
    }
}

function renderCioTable(data) {
    const tbody = document.getElementById('cioTableBody');
    tbody.innerHTML = data.map(cio => `
        <tr>
            <td>${cio.id}</td>
            <td>${cio.name || ''}</td>
            <td>${cio.unit_name || ''}</td>
            <td>${cio.phone || ''}</td>
            <td>${cio.email || ''}</td>
            <td>${cio.unit_full_name || ''}</td>
            <td>${cio.position || ''}</td>
            <td>${cio.gender || ''}</td>
            <td>${cio.home_address || ''}</td>
            <td>
                <button class="action-btn edit-btn" onclick="editCio(${cio.id})">编辑</button>
                <button class="action-btn delete-btn" onclick="deleteCio(${cio.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

function renderPagination() {
    const totalPages = Math.ceil(paginationState.total / paginationState.perPage);
    const pagination = document.getElementById('pagination');
    
    let html = '';
    
    // 上一页
    html += `<button onclick="changePage(${paginationState.page - 1})" ${paginationState.page === 1 ? 'disabled' : ''}>上一页</button>`;
    
    // 页码
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= paginationState.page - 2 && i <= paginationState.page + 2)) {
            html += `<button class="${i === paginationState.page ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
        } else if (i === paginationState.page - 3 || i === paginationState.page + 3) {
            html += `<span>...</span>`;
        }
    }
    
    // 下一页
    html += `<button onclick="changePage(${paginationState.page + 1})" ${paginationState.page === totalPages ? 'disabled' : ''}>下一页</button>`;
    
    pagination.innerHTML = html;
}

function changePage(page) {
    const totalPages = Math.ceil(paginationState.total / paginationState.perPage);
    if (page < 1 || page > totalPages) return;
    
    paginationState.page = page;
    searchCio();
}

function resetSearch() {
    document.getElementById('searchName').value = '';
    document.getElementById('searchUnit').value = '';
    document.getElementById('searchPhone').value = '';
    document.getElementById('searchFullUnit').value = '';
    paginationState.page = 1;
    
    // 隐藏查询结果统计
    document.getElementById('queryResultInfo').style.display = 'none';
    
    searchCio();
}

// 切换导出菜单显示
function toggleExportMenu() {
    const menu = document.getElementById('exportMenu');
    menu.classList.toggle('show');
}

// 点击其他地方关闭导出菜单
document.addEventListener('click', function(event) {
    const dropdown = document.querySelector('.export-dropdown');
    if (dropdown && !dropdown.contains(event.target)) {
        const menu = document.getElementById('exportMenu');
        if (menu) {
            menu.classList.remove('show');
        }
    }
});

// 导出CIO数据
async function exportCioData(format) {
    // 关闭菜单
    document.getElementById('exportMenu').classList.remove('show');
    
    // 获取当前查询条件
    const params = new URLSearchParams({
        name: document.getElementById('searchName').value,
        unit_name: document.getElementById('searchUnit').value,
        phone: document.getElementById('searchPhone').value,
        unit_full_name: document.getElementById('searchFullUnit').value,
        format: format
    });
    
    try {
        // 显示导出中提示
        const btn = document.querySelector('.export-btn');
        const originalText = btn.textContent;
        btn.textContent = '导出中...';
        btn.disabled = true;
        
        // 发送导出请求
        const response = await fetch(`${API_BASE}/api/cio/export?${params}`);
        
        if (!response.ok) {
            const result = await response.json();
            throw new Error(result.message || '导出失败');
        }
        
        // 获取文件名
        const contentDisposition = response.headers.get('content-disposition');
        let filename = `CIO名单.${format}`;
        if (contentDisposition) {
            const match = contentDisposition.match(/filename="?([^"]+)"?/);
            if (match) {
                filename = match[1];
            }
        }
        
        // 下载文件
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        alert(`导出成功！文件已保存为: ${filename}`);
        
    } catch (error) {
        alert('导出失败: ' + error.message);
    } finally {
        // 恢复按钮状态
        const btn = document.querySelector('.export-btn');
        btn.textContent = '导出Excel ▼';
        btn.disabled = false;
    }
}

async function editCio(id) {
    try {
        // 获取CIO详情
        const params = new URLSearchParams({ page: 1, per_page: 1000 });
        const response = await fetch(`${API_BASE}/api/cio?${params}`);
        const result = await response.json();
        
        if (result.success) {
            const cio = result.data.find(c => c.id === id);
            if (cio) {
                document.getElementById('cioModalTitle').textContent = '编辑CIO信息';
                document.getElementById('cioId').value = cio.id;
                document.getElementById('cioName').value = cio.name || '';
                document.getElementById('cioGender').value = cio.gender || '';
                document.getElementById('cioUnitName').value = cio.unit_name || '';
                document.getElementById('cioUnitFullName').value = cio.unit_full_name || '';
                document.getElementById('cioPhone').value = cio.phone || '';
                document.getElementById('cioEmail').value = cio.email || '';
                document.getElementById('cioPosition').value = cio.position || '';
                document.getElementById('cioHomeAddress').value = cio.home_address || '';
                document.getElementById('cioModal').classList.add('active');
            }
        }
    } catch (error) {
        alert('获取数据失败');
    }
}

function closeCioModal() {
    document.getElementById('cioModal').classList.remove('active');
}

document.getElementById('cioForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const id = document.getElementById('cioId').value;
    const data = {
        name: document.getElementById('cioName').value,
        gender: document.getElementById('cioGender').value,
        unit_name: document.getElementById('cioUnitName').value,
        unit_full_name: document.getElementById('cioUnitFullName').value,
        phone: document.getElementById('cioPhone').value,
        email: document.getElementById('cioEmail').value,
        position: document.getElementById('cioPosition').value,
        home_address: document.getElementById('cioHomeAddress').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/cio/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeCioModal();
            searchCio();
            alert(result.message);
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('保存失败，请重试');
    }
});

async function deleteCio(id) {
    if (!confirm('确定要删除该CIO信息吗？')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/cio/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            searchCio();
            alert(result.message);
        }
    } catch (error) {
        alert('删除失败，请重试');
    }
}

// ==================== 大模型配置 ====================
let llmProvidersData = {};

// 加载大模型配置
async function loadLLMConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/llm/config`);
        const result = await response.json();
        
        if (result.success) {
            const config = result.data;
            llmProvidersData = result.providers;
            
            document.getElementById('llmProvider').value = config.provider;
            document.getElementById('llmApiKey').value = config.api_key;
            document.getElementById('llmApiBase').value = config.api_base || '';
            document.getElementById('llmTemperature').value = config.temperature;
            document.getElementById('tempValue').textContent = config.temperature;
            document.getElementById('llmMaxTokens').value = config.max_tokens;
            
            onProviderChange();
            
            // 设置模型值
            const modelSelect = document.getElementById('llmModel');
            const modelCustom = document.getElementById('llmModelCustom');
            
            if (config.provider === 'custom') {
                modelSelect.style.display = 'none';
                modelCustom.style.display = 'block';
                modelCustom.value = config.model;
            } else {
                modelSelect.style.display = 'block';
                modelCustom.style.display = 'none';
                modelSelect.value = config.model;
            }
        }
    } catch (error) {
        console.error('加载配置失败:', error);
    }
}

// 提供商变更
function onProviderChange() {
    const provider = document.getElementById('llmProvider').value;
    const modelSelect = document.getElementById('llmModel');
    const modelCustom = document.getElementById('llmModelCustom');
    const apiBaseInput = document.getElementById('llmApiBase');
    
    if (provider === 'custom') {
        modelSelect.style.display = 'none';
        modelCustom.style.display = 'block';
    } else {
        modelSelect.style.display = 'block';
        modelCustom.style.display = 'none';
        
        // 更新模型选项
        const models = llmProvidersData[provider]?.models || [];
        modelSelect.innerHTML = models.map(m => `<option value="${m}">${m}</option>`).join('');
        
        // 设置默认API Base
        const defaultBase = llmProvidersData[provider]?.default_base || '';
        if (!apiBaseInput.value && defaultBase) {
            apiBaseInput.value = defaultBase;
        }
    }
}

// 保存配置
document.getElementById('llmConfigForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const provider = document.getElementById('llmProvider').value;
    const model = provider === 'custom' 
        ? document.getElementById('llmModelCustom').value 
        : document.getElementById('llmModel').value;
    
    const data = {
        provider: provider,
        api_key: document.getElementById('llmApiKey').value,
        api_base: document.getElementById('llmApiBase').value,
        model: model,
        temperature: parseFloat(document.getElementById('llmTemperature').value),
        max_tokens: parseInt(document.getElementById('llmMaxTokens').value)
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/llm/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(result.message);
            loadLLMConfig(); // 重新加载配置
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('保存失败，请重试');
    }
});

// 测试连接
async function testLLMConnection() {
    const testResult = document.getElementById('testResult');
    testResult.innerHTML = '<div class="test-result">测试中...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/llm/test`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            testResult.innerHTML = `<div class="test-result success">✓ ${result.message}</div>`;
        } else {
            testResult.innerHTML = `<div class="test-result error">✗ ${result.message}</div>`;
        }
    } catch (error) {
        testResult.innerHTML = `<div class="test-result error">✗ 测试失败: ${error.message}</div>`;
    }
}

// ==================== CIO数据库维护功能 ====================

// 查询CIO数据（用于维护页面）
async function searchCioForMaintain() {
    const params = new URLSearchParams({
        page: maintainPaginationState.page,
        per_page: maintainPaginationState.perPage,
        name: document.getElementById('maintainSearchName').value,
        unit_name: document.getElementById('maintainSearchUnit').value,
        phone: document.getElementById('maintainSearchPhone').value,
        unit_full_name: document.getElementById('maintainSearchFullUnit').value
    });
    
    try {
        const response = await fetch(`${API_BASE}/api/cio?${params}`);
        const result = await response.json();
        
        if (result.success) {
            renderCioMaintainTable(result.data);
            maintainPaginationState.total = result.total;
            renderMaintainPagination();
            updateSelectedCount();
        }
    } catch (error) {
        console.error('查询失败:', error);
    }
}

// 渲染CIO维护表格
function renderCioMaintainTable(data) {
    const tbody = document.getElementById('cioMaintainTableBody');
    tbody.innerHTML = data.map(cio => `
        <tr data-id="${cio.id}" class="${selectedCioIds.has(cio.id) ? 'selected' : ''}">
            <td><input type="checkbox" ${selectedCioIds.has(cio.id) ? 'checked' : ''} onchange="toggleRowSelection(${cio.id}, this.checked)"></td>
            <td>${cio.id}</td>
            <td>${cio.name || ''}</td>
            <td>${cio.unit_name || ''}</td>
            <td>${cio.phone || ''}</td>
            <td>${cio.email || ''}</td>
            <td>${cio.unit_full_name || ''}</td>
            <td>${cio.position || ''}</td>
            <td>${cio.gender || ''}</td>
            <td>${cio.home_address || ''}</td>
            <td>
                <button class="action-btn edit-btn" onclick="editCioInMaintain(${cio.id})">编辑</button>
                <button class="action-btn delete-btn" onclick="deleteSingleCio(${cio.id})">删除</button>
            </td>
        </tr>
    `).join('');
}

// 渲染维护页面分页
function renderMaintainPagination() {
    const totalPages = Math.ceil(maintainPaginationState.total / maintainPaginationState.perPage);
    const pagination = document.getElementById('maintainPagination');
    
    let html = '';
    
    html += `<button onclick="changeMaintainPage(${maintainPaginationState.page - 1})" ${maintainPaginationState.page === 1 ? 'disabled' : ''}>上一页</button>`;
    
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= maintainPaginationState.page - 2 && i <= maintainPaginationState.page + 2)) {
            html += `<button class="${i === maintainPaginationState.page ? 'active' : ''}" onclick="changeMaintainPage(${i})">${i}</button>`;
        } else if (i === maintainPaginationState.page - 3 || i === maintainPaginationState.page + 3) {
            html += `<span>...</span>`;
        }
    }
    
    html += `<button onclick="changeMaintainPage(${maintainPaginationState.page + 1})" ${maintainPaginationState.page === totalPages ? 'disabled' : ''}>下一页</button>`;
    
    pagination.innerHTML = html;
}

// 切换维护页面
function changeMaintainPage(page) {
    const totalPages = Math.ceil(maintainPaginationState.total / maintainPaginationState.perPage);
    if (page < 1 || page > totalPages) return;
    
    maintainPaginationState.page = page;
    searchCioForMaintain();
}

// 重置维护页面搜索
function resetMaintainSearch() {
    document.getElementById('maintainSearchName').value = '';
    document.getElementById('maintainSearchUnit').value = '';
    document.getElementById('maintainSearchPhone').value = '';
    document.getElementById('maintainSearchFullUnit').value = '';
    maintainPaginationState.page = 1;
    selectedCioIds.clear();
    document.getElementById('headerCheckbox').checked = false;
    searchCioForMaintain();
}

// 切换行选择
function toggleRowSelection(id, checked) {
    if (checked) {
        selectedCioIds.add(id);
    } else {
        selectedCioIds.delete(id);
    }
    
    // 更新行样式
    const row = document.querySelector(`tr[data-id="${id}"]`);
    if (row) {
        row.classList.toggle('selected', checked);
    }
    
    updateSelectedCount();
}

// 全选
function selectAllRows() {
    const checkboxes = document.querySelectorAll('#cioMaintainTableBody input[type="checkbox"]');
    const rows = document.querySelectorAll('#cioMaintainTableBody tr');
    
    checkboxes.forEach((checkbox, index) => {
        checkbox.checked = true;
        const id = parseInt(rows[index].getAttribute('data-id'));
        selectedCioIds.add(id);
        rows[index].classList.add('selected');
    });
    
    document.getElementById('headerCheckbox').checked = true;
    updateSelectedCount();
}

// 反选
function invertSelection() {
    const checkboxes = document.querySelectorAll('#cioMaintainTableBody input[type="checkbox"]');
    const rows = document.querySelectorAll('#cioMaintainTableBody tr');
    
    checkboxes.forEach((checkbox, index) => {
        checkbox.checked = !checkbox.checked;
        const id = parseInt(rows[index].getAttribute('data-id'));
        
        if (checkbox.checked) {
            selectedCioIds.add(id);
            rows[index].classList.add('selected');
        } else {
            selectedCioIds.delete(id);
            rows[index].classList.remove('selected');
        }
    });
    
    // 更新表头复选框状态
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    document.getElementById('headerCheckbox').checked = allChecked;
    
    updateSelectedCount();
}

// 表头复选框切换
function toggleHeaderCheckbox() {
    const headerCheckbox = document.getElementById('headerCheckbox');
    if (headerCheckbox.checked) {
        selectAllRows();
    } else {
        // 取消全选
        const checkboxes = document.querySelectorAll('#cioMaintainTableBody input[type="checkbox"]');
        const rows = document.querySelectorAll('#cioMaintainTableBody tr');
        
        checkboxes.forEach((checkbox, index) => {
            checkbox.checked = false;
            const id = parseInt(rows[index].getAttribute('data-id'));
            selectedCioIds.delete(id);
            rows[index].classList.remove('selected');
        });
        
        updateSelectedCount();
    }
}

// 更新选中计数
function updateSelectedCount() {
    const count = selectedCioIds.size;
    document.getElementById('selectedCount').textContent = `已选择 ${count} 条`;
    document.getElementById('batchDeleteBtn').disabled = count === 0;
}

// 确认批量删除
function confirmBatchDelete() {
    const count = selectedCioIds.size;
    if (count === 0) return;
    
    document.getElementById('confirmDeleteMsg').innerHTML = 
        `确定要删除选中的 <strong>${count}</strong> 条数据吗？<br>此操作不可恢复！`;
    document.getElementById('confirmDeleteModal').classList.add('active');
}

// 关闭确认删除模态框
function closeConfirmDeleteModal() {
    document.getElementById('confirmDeleteModal').classList.remove('active');
}

// 执行批量删除
async function executeBatchDelete() {
    closeConfirmDeleteModal();
    
    const ids = Array.from(selectedCioIds);
    let successCount = 0;
    let failCount = 0;
    
    for (const id of ids) {
        try {
            const response = await fetch(`${API_BASE}/api/cio/${id}`, {
                method: 'DELETE'
            });
            
            const result = await response.json();
            
            if (result.success) {
                successCount++;
            } else {
                failCount++;
            }
        } catch (error) {
            failCount++;
        }
    }
    
    // 清空选择
    selectedCioIds.clear();
    document.getElementById('headerCheckbox').checked = false;
    
    // 刷新数据
    searchCioForMaintain();
    
    // 显示结果
    if (failCount === 0) {
        alert(`成功删除 ${successCount} 条数据`);
    } else {
        alert(`删除完成：成功 ${successCount} 条，失败 ${failCount} 条`);
    }
}

// 删除单个CIO
async function deleteSingleCio(id) {
    if (!confirm('确定要删除这条CIO信息吗？\n此操作不可恢复！')) return;
    
    try {
        const response = await fetch(`${API_BASE}/api/cio/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('删除成功');
            searchCioForMaintain();
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('删除失败，请重试');
    }
}

// 在维护页面编辑CIO
async function editCioInMaintain(id) {
    try {
        const params = new URLSearchParams({ page: 1, per_page: 1000 });
        const response = await fetch(`${API_BASE}/api/cio?${params}`);
        const result = await response.json();
        
        if (result.success) {
            const cio = result.data.find(c => c.id === id);
            if (cio) {
                document.getElementById('cioModalTitle').textContent = '编辑CIO信息';
                document.getElementById('cioId').value = cio.id;
                document.getElementById('cioName').value = cio.name || '';
                document.getElementById('cioGender').value = cio.gender || '';
                document.getElementById('cioUnitName').value = cio.unit_name || '';
                document.getElementById('cioUnitFullName').value = cio.unit_full_name || '';
                document.getElementById('cioPhone').value = cio.phone || '';
                document.getElementById('cioEmail').value = cio.email || '';
                document.getElementById('cioPosition').value = cio.position || '';
                document.getElementById('cioHomeAddress').value = cio.home_address || '';
                document.getElementById('cioModal').classList.add('active');
                
                // 修改保存后的回调
                document.getElementById('cioForm').onsubmit = async function(e) {
                    e.preventDefault();
                    await saveCioEdit(id, true);
                };
            }
        }
    } catch (error) {
        alert('获取数据失败');
    }
}

// 保存CIO编辑
async function saveCioEdit(id, isMaintainPage) {
    const data = {
        name: document.getElementById('cioName').value,
        gender: document.getElementById('cioGender').value,
        unit_name: document.getElementById('cioUnitName').value,
        unit_full_name: document.getElementById('cioUnitFullName').value,
        phone: document.getElementById('cioPhone').value,
        email: document.getElementById('cioEmail').value,
        position: document.getElementById('cioPosition').value,
        home_address: document.getElementById('cioHomeAddress').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/cio/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeCioModal();
            if (isMaintainPage) {
                searchCioForMaintain();
            } else {
                searchCio();
            }
            alert(result.message);
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('保存失败，请重试');
    }
}

// 打开新增CIO模态框
function openAddCioModal() {
    document.getElementById('addCioForm').reset();
    document.getElementById('addCioModal').classList.add('active');
}

// 关闭新增CIO模态框
function closeAddCioModal() {
    document.getElementById('addCioModal').classList.remove('active');
}

// 新增CIO表单提交
document.getElementById('addCioForm')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const data = {
        name: document.getElementById('addCioName').value,
        gender: document.getElementById('addCioGender').value,
        unit_name: document.getElementById('addCioUnitName').value,
        unit_full_name: document.getElementById('addCioUnitFullName').value,
        phone: document.getElementById('addCioPhone').value,
        email: document.getElementById('addCioEmail').value,
        position: document.getElementById('addCioPosition').value,
        home_address: document.getElementById('addCioHomeAddress').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/cio`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            closeAddCioModal();
            searchCioForMaintain();
            alert(result.message);
        } else {
            alert(result.message);
        }
    } catch (error) {
        alert('保存失败，请重试');
    }
});
