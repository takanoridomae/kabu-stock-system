// 企業管理画面のJavaScript機能

// グローバル変数
let allCompanies = [];
let currentEditingCompany = null;
let deleteStage = 0; // 0: 初期状態, 1: 依存関係確認済み, 2: 最終確認
let currentDetailCompanyId = null; // 詳細表示中の企業ID

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', function() {
    loadCompanies();
    setupEventListeners();
});

// イベントリスナーの設定
function setupEventListeners() {
    // フィルタリング用イベント
    ['filterSymbol', 'filterName', 'filterSector'].forEach(id => {
        document.getElementById(id).addEventListener('input', debounce(applyFilter, 300));
    });
    
    // モーダルが閉じられた時のリセット
    const companyModal = document.getElementById('companyModal');
    companyModal.addEventListener('hidden.bs.modal', resetCompanyForm);
    
    const deleteModal = document.getElementById('deleteModal');
    deleteModal.addEventListener('hidden.bs.modal', () => {
        deleteStage = 0;
        currentEditingCompany = null;
    });
    
    const dependencyModal = document.getElementById('dependencyModal');
    dependencyModal.addEventListener('hidden.bs.modal', () => {
        deleteStage = 0;
    });
}

// デバウンス関数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 企業一覧を読み込み（詳細データ付き）
async function loadCompanies() {
    try {
        showLoading(true);
        
        // 詳細な企業検索APIを使用（株価、財務データも含む）
        const response = await fetch('/api/companies/search', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})  // 空で全件検索
        });
        const result = await response.json();
        
        if (result.success) {
            allCompanies = result.data;
            displayCompanies(allCompanies);
            showAlert('success', `${result.count}件の企業を読み込みました`);
        } else {
            showAlert('danger', 'データの読み込みに失敗しました: ' + result.error);
        }
    } catch (error) {
        console.error('Error loading companies:', error);
        showAlert('danger', 'データの読み込み中にエラーが発生しました');
    } finally {
        showLoading(false);
    }
}

// 企業一覧を表示
function displayCompanies(companies) {
    const tbody = document.getElementById('companiesTableBody');
    
    if (companies.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted">
                    <i class="fas fa-info-circle me-2"></i>表示する企業がありません
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = companies.map(company => {
        const currentPrice = company.current_price ? 
            `¥${Number(company.current_price).toLocaleString()}` : '-';
        const pbr = company.pbr ? Number(company.pbr).toFixed(2) : '-';
        const per = company.per ? Number(company.per).toFixed(2) : '-';
        const lastUpdate = company.price_date || company.report_date || company.updated_at;
        
        return `
            <tr>
                <td><code>${escapeHtml(company.symbol)}</code></td>
                <td>${escapeHtml(company.name)}</td>
                <td>${escapeHtml(company.sector || '-')}</td>
                <td>${escapeHtml(company.market || '-')}</td>
                <td class="text-end">
                    <span class="${company.current_price ? 'text-primary fw-bold' : 'text-muted'}">${currentPrice}</span>
                    ${company.price_date ? `<br><small class="text-muted">${formatDate(company.price_date)}</small>` : ''}
                </td>
                <td class="text-center">
                    <span class="${company.pbr ? 'badge bg-info' : 'text-muted'}">${pbr}</span>
                </td>
                <td class="text-center">
                    <span class="${company.per ? 'badge bg-success' : 'text-muted'}">${per}</span>
                </td>
                <td><small class="text-muted">${formatDateTime(lastUpdate)}</small></td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-info" 
                                onclick="showCompanyDetail(${company.id})" 
                                title="詳細表示">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-primary" 
                                onclick="editCompany(${company.id})" 
                                title="編集">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" 
                                onclick="confirmDeleteCompany(${company.id})" 
                                title="削除">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// フィルターを適用
function applyFilter() {
    const symbolFilter = document.getElementById('filterSymbol').value.toLowerCase();
    const nameFilter = document.getElementById('filterName').value.toLowerCase();
    const sectorFilter = document.getElementById('filterSector').value.toLowerCase();
    
    const filteredCompanies = allCompanies.filter(company => {
        return (
            (symbolFilter === '' || company.symbol.toLowerCase().includes(symbolFilter)) &&
            (nameFilter === '' || company.name.toLowerCase().includes(nameFilter)) &&
            (sectorFilter === '' || (company.sector && company.sector.toLowerCase().includes(sectorFilter)))
        );
    });
    
    displayCompanies(filteredCompanies);
}

// フィルターをクリア
function clearFilter() {
    document.getElementById('filterSymbol').value = '';
    document.getElementById('filterName').value = '';
    document.getElementById('filterSector').value = '';
    displayCompanies(allCompanies);
}

// 新規企業登録モーダルを表示
function showCreateModal() {
    resetCompanyForm();
    document.getElementById('companyModalTitle').innerHTML = 
        '<i class="fas fa-plus me-2"></i>新規企業登録';
    document.getElementById('saveCompanyBtn').innerHTML = 
        '<i class="fas fa-save me-1"></i>登録';
    
    const modal = new bootstrap.Modal(document.getElementById('companyModal'));
    modal.show();
}

// 企業編集
function editCompany(companyId) {
    const company = allCompanies.find(c => c.id === companyId);
    if (!company) {
        showAlert('danger', '企業データが見つかりません');
        return;
    }
    
    currentEditingCompany = company;
    
    // フォームに値を設定
    document.getElementById('companyId').value = company.id;
    document.getElementById('companySymbol').value = company.symbol;
    document.getElementById('companyName').value = company.name;
    document.getElementById('companySector').value = company.sector || '';
    document.getElementById('companyMarket').value = company.market || '';
    
    // モーダルのタイトルを変更
    document.getElementById('companyModalTitle').innerHTML = 
        '<i class="fas fa-edit me-2"></i>企業情報編集';
    document.getElementById('saveCompanyBtn').innerHTML = 
        '<i class="fas fa-save me-1"></i>更新';
    
    const modal = new bootstrap.Modal(document.getElementById('companyModal'));
    modal.show();
}

// 企業名から検索
async function searchCompanyByName() {
    const companyName = document.getElementById('searchCompanyName').value.trim();
    
    console.log('検索開始:', companyName); // デバッグログ
    
    if (!companyName) {
        showAlert('warning', '企業名を入力してください');
        return;
    }
    
    try {
        console.log('API リクエスト送信中...'); // デバッグログ
        
        const response = await fetch('/api/companies/search-by-name', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ company_name: companyName })
        });
        
        console.log('API レスポンス:', response.status); // デバッグログ
        
        const result = await response.json();
        console.log('API 結果:', result); // デバッグログ
        
        if (result.success && result.data.length > 0) {
            console.log('検索結果を表示:', result.data.length, '件'); // デバッグログ
            displaySearchResults(result.data);
        } else {
            console.log('検索結果なし'); // デバッグログ
            document.getElementById('searchResults').innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>該当する企業が見つかりませんでした
                </div>
            `;
            document.getElementById('searchResults').style.display = 'block';
        }
    } catch (error) {
        console.error('Error searching company:', error);
        showAlert('danger', '検索中にエラーが発生しました: ' + error.message);
    }
}

// 検索結果を表示
function displaySearchResults(companies) {
    const resultsDiv = document.getElementById('searchResults');
    
    resultsDiv.innerHTML = `
        <h6><i class="fas fa-search-plus me-2"></i>J-Quants API検索結果 (${companies.length}件)</h6>
        <div class="search-results-list">
            ${companies.map(company => {
                const isRegistered = company.already_registered;
                const statusBadge = isRegistered ? 
                    '<span class="badge bg-secondary ms-2">登録済み</span>' : 
                    '<span class="badge bg-success ms-2">新規</span>';
                
                return `
                    <div class="search-result-item ${isRegistered ? 'border-secondary' : ''}" 
                         onclick="selectSearchResult('${escapeHtml(company.symbol)}', '${escapeHtml(company.name)}', '${escapeHtml(company.sector || '')}', '${escapeHtml(company.market || '')}')">
                        <div class="d-flex justify-content-between align-items-start">
                            <div class="flex-grow-1">
                                <div class="fw-bold">
                                    <strong>${escapeHtml(company.symbol)}</strong> - ${escapeHtml(company.name)}
                                    ${statusBadge}
                                </div>
                                ${company.name_english ? `<div class="text-muted small">${escapeHtml(company.name_english)}</div>` : ''}
                                <div class="text-muted small mt-1">
                                    <i class="fas fa-industry me-1"></i>${escapeHtml(company.sector || '-')} | 
                                    <i class="fas fa-chart-line me-1"></i>${escapeHtml(company.market || '-')}
                                    ${company.listing_date ? ` | 上場日: ${company.listing_date}` : ''}
                                </div>
                            </div>
                            <div class="text-end">
                                <small class="text-muted">J-Quants</small>
                            </div>
                        </div>
                    </div>
                `;
            }).join('')}
        </div>
        <div class="alert alert-info mt-2">
            <i class="fas fa-info-circle me-2"></i>
            J-Quants APIから全上場企業のデータを検索しています。「新規」の企業を選択して登録できます。
        </div>
    `;
    
    resultsDiv.style.display = 'block';
}

// 検索結果を選択
function selectSearchResult(symbol, name, sector, market) {
    document.getElementById('companySymbol').value = symbol;
    document.getElementById('companyName').value = name;
    document.getElementById('companySector').value = sector;
    document.getElementById('companyMarket').value = market;
    
    // 選択されたアイテムをハイライト
    document.querySelectorAll('.search-result-item').forEach(item => {
        item.classList.remove('selected');
    });
    event.target.closest('.search-result-item').classList.add('selected');
    
    showAlert('success', '企業情報が自動入力されました');
}

// 企業情報を保存
async function saveCompany() {
    const symbol = document.getElementById('companySymbol').value.trim();
    const name = document.getElementById('companyName').value.trim();
    const sector = document.getElementById('companySector').value.trim();
    const market = document.getElementById('companyMarket').value.trim();
    const companyId = document.getElementById('companyId').value;
    
    // バリデーション
    if (!symbol || !name) {
        showAlert('warning', '企業コードと企業名は必須です');
        return;
    }
    
    if (!/^\d{4,5}$/.test(symbol)) {
        showAlert('warning', '企業コードは4桁または5桁の数字で入力してください');
        return;
    }
    
    const data = { symbol, name, sector, market };
    const isEdit = Boolean(companyId);
    
    try {
        const url = isEdit ? `/api/companies/${companyId}/update` : '/api/companies/create';
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', result.message);
            
            // モーダルを閉じる
            const modal = bootstrap.Modal.getInstance(document.getElementById('companyModal'));
            modal.hide();
            
            // 一覧を更新
            await loadCompanies();
        } else {
            showAlert('danger', result.error);
        }
    } catch (error) {
        console.error('Error saving company:', error);
        showAlert('danger', '保存中にエラーが発生しました');
    }
}

// 企業削除の確認（2段階確認）
async function confirmDeleteCompany(companyId) {
    const company = allCompanies.find(c => c.id === companyId);
    if (!company) {
        showAlert('danger', '企業データが見つかりません');
        return;
    }
    
    currentEditingCompany = company;
    deleteStage = 0;
    
    try {
        // まず関連データをチェック
        const response = await fetch(`/api/companies/${companyId}/check-dependencies`);
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            
            if (data.has_dependencies) {
                // 関連データがある場合は依存関係モーダルを表示
                showDependencyModal(data);
            } else {
                // 関連データがない場合は直接削除確認
                showDeleteModal(company, data);
            }
        } else {
            showAlert('danger', 'データの確認に失敗しました: ' + result.error);
        }
    } catch (error) {
        console.error('Error checking dependencies:', error);
        showAlert('danger', 'データの確認中にエラーが発生しました');
    }
}

// 依存関係モーダルを表示（1回目の確認）
function showDependencyModal(data) {
    const dependencies = data.dependencies;
    const company = data.company;
    
    const dependencyContent = document.getElementById('dependencyContent');
    dependencyContent.innerHTML = `
        <div class="mb-3">
            <h6><i class="fas fa-building me-2"></i>削除対象企業</h6>
            <div class="alert alert-secondary">
                <strong>${escapeHtml(company.symbol)}</strong> - ${escapeHtml(company.name)}
            </div>
        </div>
        
        <h6><i class="fas fa-database me-2"></i>関連データ</h6>
        
        ${Object.entries(dependencies).map(([key, count]) => {
            if (count === 0) return '';
            
            const labels = {
                'stock_prices': '株価データ',
                'financial_metrics': '財務指標',
                'price_statistics': '価格統計',
                'technical_indicators': 'テクニカル指標'
            };
            
            return `
                <div class="dependency-info">
                    <span><i class="fas fa-chart-bar me-2"></i>${labels[key]}</span>
                    <span class="dependency-count">${count.toLocaleString()}件</span>
                </div>
            `;
        }).join('')}
        
        <div class="mt-3">
            <strong>合計削除データ数: ${data.total_data_count.toLocaleString()}件</strong>
        </div>
    `;
    
    // 続行ボタンのクリックイベントを設定
    document.getElementById('proceedDeleteBtn').onclick = () => {
        const modal = bootstrap.Modal.getInstance(document.getElementById('dependencyModal'));
        modal.hide();
        
        // 最終確認モーダルを表示
        setTimeout(() => {
            showDeleteModal(company, data);
        }, 300);
    };
    
    const modal = new bootstrap.Modal(document.getElementById('dependencyModal'));
    modal.show();
}

// 削除確認モーダルを表示（2回目の確認）
function showDeleteModal(company, dependencyData) {
    deleteStage = 1;
    
    const deleteContent = document.getElementById('deleteContent');
    deleteContent.innerHTML = `
        <div class="alert alert-danger">
            <h6><i class="fas fa-exclamation-triangle me-2"></i>最終確認</h6>
            <p class="mb-0">以下の企業とすべての関連データを完全に削除します。</p>
        </div>
        
        <div class="card">
            <div class="card-body">
                <h6 class="card-title">${escapeHtml(company.symbol)} - ${escapeHtml(company.name)}</h6>
                <div class="row">
                    <div class="col-md-6">
                        <small class="text-muted">業種:</small> ${escapeHtml(company.sector || '-')}
                    </div>
                    <div class="col-md-6">
                        <small class="text-muted">市場:</small> ${escapeHtml(company.market || '-')}
                    </div>
                </div>
            </div>
        </div>
        
        ${dependencyData.has_dependencies ? `
            <div class="mt-3">
                <small class="text-muted">
                    <i class="fas fa-info-circle me-1"></i>
                    ${dependencyData.total_data_count.toLocaleString()}件の関連データも同時に削除されます
                </small>
            </div>
        ` : ''}
        
        <div class="mt-3">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="confirmDeleteCheck">
                <label class="form-check-label" for="confirmDeleteCheck">
                    <strong>削除を実行することを理解し、同意します</strong>
                </label>
            </div>
        </div>
    `;
    
    // 削除ボタンのクリックイベントを設定
    document.getElementById('confirmDeleteBtn').onclick = () => {
        const checkbox = document.getElementById('confirmDeleteCheck');
        if (!checkbox.checked) {
            showAlert('warning', '削除の同意にチェックを入れてください');
            return;
        }
        executeDelete(company.id);
    };
    
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

// 削除を実行
async function executeDelete(companyId) {
    try {
        const response = await fetch(`/api/companies/${companyId}/delete`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', result.message);
            
            // モーダルを閉じる
            const modal = bootstrap.Modal.getInstance(document.getElementById('deleteModal'));
            modal.hide();
            
            // 一覧を更新
            await loadCompanies();
        } else {
            showAlert('danger', result.error);
        }
    } catch (error) {
        console.error('Error deleting company:', error);
        showAlert('danger', '削除中にエラーが発生しました');
    }
}

// フォームをリセット
function resetCompanyForm() {
    document.getElementById('companyForm').reset();
    document.getElementById('companyId').value = '';
    document.getElementById('searchCompanyName').value = '';
    document.getElementById('searchResults').style.display = 'none';
    currentEditingCompany = null;
}

// 読み込み中表示の切り替え
function showLoading(show) {
    const tbody = document.getElementById('companiesTableBody');
    if (show) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center">
                    <i class="fas fa-spinner fa-spin me-2"></i>読み込み中...
                </td>
            </tr>
        `;
    }
}

// アラート表示
function showAlert(type, message) {
    const alertArea = document.getElementById('alertArea');
    const alertId = 'alert-' + Date.now();
    
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
            ${escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertArea.insertAdjacentHTML('beforeend', alertHtml);
    
    // 5秒後に自動で閉じる
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const alert = bootstrap.Alert.getOrCreateInstance(alertElement);
            alert.close();
        }
    }, 5000);
}

// HTML エスケープ
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 日付フォーマット
function formatDate(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ja-JP');
    } catch (error) {
        return dateString;
    }
}

// 日時フォーマット
function formatDateTime(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ja-JP') + ' ' + date.toLocaleTimeString('ja-JP', {hour: '2-digit', minute: '2-digit'});
    } catch (error) {
        return dateString;
    }
}

// 企業詳細表示
async function showCompanyDetail(companyId) {
    try {
        currentDetailCompanyId = companyId;
        
        // モーダルを表示（読み込み中状態）
        const modal = new bootstrap.Modal(document.getElementById('companyDetailModal'));
        modal.show();
        
        // 読み込み中表示
        document.getElementById('detailLoading').style.display = 'block';
        document.getElementById('detailContent').style.display = 'none';
        document.getElementById('detailError').style.display = 'none';
        
        // 企業詳細データを取得
        const response = await fetch(`/api/companies/${companyId}`);
        const result = await response.json();
        
        if (result.success) {
            displayCompanyDetail(result.data);
        } else {
            showDetailError(result.error);
        }
    } catch (error) {
        console.error('Error loading company detail:', error);
        showDetailError('詳細データの読み込み中にエラーが発生しました');
    }
}

// 企業詳細データを表示
function displayCompanyDetail(company) {
    // 読み込み中を非表示にして詳細を表示
    document.getElementById('detailLoading').style.display = 'none';
    document.getElementById('detailContent').style.display = 'block';
    document.getElementById('detailError').style.display = 'none';
    
    // モーダルタイトルを更新
    document.getElementById('companyDetailModalTitle').innerHTML = 
        `<i class="fas fa-chart-line me-2"></i>${escapeHtml(company.symbol)} - ${escapeHtml(company.name)}`;
    
    // 基本情報
    document.getElementById('detail-symbol').textContent = company.symbol;
    document.getElementById('detail-name').textContent = company.name;
    document.getElementById('detail-sector').textContent = company.sector || '-';
    document.getElementById('detail-market').textContent = company.market || '-';
    document.getElementById('detail-created').textContent = formatDate(company.created_at);
    
    // 株価情報
    const latestPrice = company.price_history && company.price_history.length > 0 ? company.price_history[0] : null;
    if (latestPrice) {
        document.getElementById('detail-current-price').textContent = `¥${Number(latestPrice.price).toLocaleString()}`;
        document.getElementById('detail-price-date').textContent = formatDate(latestPrice.price_date);
        document.getElementById('detail-volume').textContent = latestPrice.volume ? Number(latestPrice.volume).toLocaleString() : '-';
    } else {
        document.getElementById('detail-current-price').textContent = '-';
        document.getElementById('detail-price-date').textContent = '-';
        document.getElementById('detail-volume').textContent = '-';
    }
    
    // 価格統計情報
    const stats = company.price_statistics || [];
    const monthlyStats = stats.find(s => s.period_type === 'monthly') || {};
    const yearlyStats = stats.find(s => s.period_type === 'yearly') || {};
    
    document.getElementById('detail-monthly-max').textContent = 
        monthlyStats.max_price ? `¥${Number(monthlyStats.max_price).toLocaleString()}` : '-';
    document.getElementById('detail-monthly-min').textContent = 
        monthlyStats.min_price ? `¥${Number(monthlyStats.min_price).toLocaleString()}` : '-';
    document.getElementById('detail-yearly-max').textContent = 
        yearlyStats.max_price ? `¥${Number(yearlyStats.max_price).toLocaleString()}` : '-';
    document.getElementById('detail-yearly-min').textContent = 
        yearlyStats.min_price ? `¥${Number(yearlyStats.min_price).toLocaleString()}` : '-';
    
    // 財務指標
    const financial = company.financial_metrics || {};
    document.getElementById('detail-pbr').textContent = 
        financial.pbr ? Number(financial.pbr).toFixed(2) : '-';
    document.getElementById('detail-per').textContent = 
        financial.per ? Number(financial.per).toFixed(2) : '-';
    document.getElementById('detail-equity-ratio').textContent = 
        financial.equity_ratio ? (Number(financial.equity_ratio) * 100).toFixed(1) + '%' : '-';
    document.getElementById('detail-roe').textContent = 
        financial.roe ? (Number(financial.roe) * 100).toFixed(1) + '%' : '-';
    document.getElementById('detail-roa').textContent = 
        financial.roa ? (Number(financial.roa) * 100).toFixed(1) + '%' : '-';
    document.getElementById('detail-report-date').textContent = 
        financial.report_date ? formatDate(financial.report_date) : '-';
    
    // 売上高・営業利益
    document.getElementById('detail-net-sales').textContent = 
        financial.net_sales ? `¥${(Number(financial.net_sales) / 1000000000000).toFixed(1)}兆円` : '-';
    document.getElementById('detail-net-sales-date').textContent = 
        financial.net_sales_date ? formatDate(financial.net_sales_date) : '-';
    document.getElementById('detail-operating-profit').textContent = 
        financial.operating_profit ? `¥${(Number(financial.operating_profit) / 1000000000000).toFixed(1)}兆円` : '-';
    document.getElementById('detail-operating-profit-date').textContent = 
        financial.operating_profit_date ? formatDate(financial.operating_profit_date) : '-';
}

// 詳細表示エラー
function showDetailError(message) {
    document.getElementById('detailLoading').style.display = 'none';
    document.getElementById('detailContent').style.display = 'none';
    document.getElementById('detailError').style.display = 'block';
    document.getElementById('detailErrorMessage').textContent = message;
}

// 詳細データの更新
async function refreshDetailData() {
    if (currentDetailCompanyId) {
        await showCompanyDetail(currentDetailCompanyId);
    }
}

// 株価データ取得（詳細モーダル内から）
async function fetchStockData() {
    if (!currentDetailCompanyId) return;
    
    try {
        const company = allCompanies.find(c => c.id === currentDetailCompanyId);
        if (!company) return;
        
        showAlert('info', `${company.symbol} の株価データ取得を開始しています...`);
        
        const response = await fetch(`/api/stock-data/fetch/${company.symbol}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ force_update: true })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', result.message);
            // 詳細データを更新
            await refreshDetailData();
            // 一覧も更新
            await loadCompanies();
        } else {
            showAlert('danger', 'データ取得に失敗しました: ' + result.error);
        }
    } catch (error) {
        console.error('Error fetching stock data:', error);
        showAlert('danger', '株価データ取得中にエラーが発生しました');
    }
}

// J-Quants APIデータ取得（詳細モーダル内から）
async function fetchJQuantsData() {
    if (!currentDetailCompanyId) return;
    
    try {
        const company = allCompanies.find(c => c.id === currentDetailCompanyId);
        if (!company) return;
        
        showAlert('info', `${company.symbol} のJ-Quants APIデータ取得を開始しています...`);
        
        const response = await fetch(`/api/jquants-data/fetch/${company.symbol}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ force_update: true })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', result.message);
            // 詳細データを更新
            await refreshDetailData();
            // 一覧も更新
            await loadCompanies();
        } else {
            showAlert('danger', 'J-Quants API取得に失敗しました: ' + result.error);
        }
    } catch (error) {
        console.error('Error fetching J-Quants data:', error);
        showAlert('danger', 'J-Quants APIデータ取得中にエラーが発生しました');
    }
}

// 手動データ入力機能
function showManualDataEntryModal() {
    const modal = new bootstrap.Modal(document.getElementById('manualDataEntryModal'));
    modal.show();
    
    // 企業リストを読み込み
    loadCompaniesForManualEntry();
    
    // 今日の日付をデフォルトに設定
    document.getElementById('manualDate').valueAsDate = new Date();
}

function loadCompaniesForManualEntry() {
    fetch('/api/companies')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('manualSymbol');
            select.innerHTML = '<option value="">企業を選択してください</option>';
            
            if (data.success) {
                data.data.forEach(company => {
                    const option = document.createElement('option');
                    option.value = company.symbol;
                    option.textContent = `${company.symbol} - ${company.name}`;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('企業一覧の取得に失敗:', error);
            showAlert('danger', '企業一覧の取得に失敗しました');
        });
}

function saveManualData() {
    const form = document.getElementById('manualDataForm');
    
    // バリデーション
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    const symbol = document.getElementById('manualSymbol').value;
    const date = document.getElementById('manualDate').value;
    const price = document.getElementById('manualPrice').value;
    const volume = document.getElementById('manualVolume').value;
    const pbr = document.getElementById('manualPBR').value;
    const per = document.getElementById('manualPER').value;
    const roe = document.getElementById('manualROE').value;
    const equityRatio = document.getElementById('manualEquityRatio').value;
    const roa = document.getElementById('manualROA').value;
    const netSales = document.getElementById('manualNetSales').value;
    const operatingProfit = document.getElementById('manualOperatingProfit').value;
    
    if (!symbol || !date) {
        showAlert('warning', '企業コードとデータ日付は必須です');
        return;
    }
    
    // データの構築
    const requestData = {
        symbol: symbol,
        price_date: date,
        report_date: date  // 財務指標用の日付も同じ日付を使用
    };
    
    // 株価データ
    if (price) requestData.price = parseFloat(price);
    if (volume) requestData.volume = parseInt(volume);
    
    // 財務指標データ
    if (pbr) requestData.pbr = parseFloat(pbr);
    if (per) requestData.per = parseFloat(per);
    if (roe) requestData.roe = parseFloat(roe) / 100; // %を小数に変換
    if (equityRatio) requestData.equity_ratio = parseFloat(equityRatio) / 100;
    if (roa) requestData.roa = parseFloat(roa) / 100;
    if (netSales) requestData.net_sales = parseFloat(netSales);
    if (operatingProfit) requestData.operating_profit = parseFloat(operatingProfit);
    
    // データ保存
    fetch('/api/companies/register', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('success', `${symbol} のデータを手動で保存しました`);
            
            // フォームをクリア
            form.reset();
            document.getElementById('manualDate').valueAsDate = new Date();
            
            // 企業一覧を更新
            loadCompanies();
            
            // モーダルを閉じる
            const modal = bootstrap.Modal.getInstance(document.getElementById('manualDataEntryModal'));
            modal.hide();
            
        } else {
            showAlert('danger', 'データの保存に失敗しました: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Manual data save error:', error);
        showAlert('danger', 'データ保存中にエラーが発生しました');
    });
}
