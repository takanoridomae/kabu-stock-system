/**
 * 株式検索システム - 共通JavaScript関数
 */

// グローバル変数
let alertTimeout;

/**
 * アラート表示関数
 * @param {string} message - 表示するメッセージ
 * @param {string} type - アラートタイプ (success, danger, warning, info)
 * @param {number} duration - 表示時間（ミリ秒）
 */
function showAlert(message, type = 'info', duration = 5000) {
    const alertArea = document.getElementById('alertArea');
    if (!alertArea) return;
    
    // 既存のアラートをクリア
    if (alertTimeout) {
        clearTimeout(alertTimeout);
    }
    
    // アラート要素を作成
    const alertId = 'alert-' + Date.now();
    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    
    alertArea.innerHTML = alertHTML;
    
    // 自動で非表示にする
    if (duration > 0) {
        alertTimeout = setTimeout(() => {
            const alertElement = document.getElementById(alertId);
            if (alertElement) {
                const bsAlert = new bootstrap.Alert(alertElement);
                bsAlert.close();
            }
        }, duration);
    }
}

/**
 * アラートタイプに応じたアイコンを取得
 * @param {string} type - アラートタイプ
 * @returns {string} Font Awesomeアイコンクラス
 */
function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

/**
 * データエクスポート関数
 */
function exportData() {
    showAlert('データをエクスポートしています...', 'info');
    
    fetch('/api/export')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showAlert(data.message, 'success');
                
                // ダウンロードリンクを作成（オプション）
                if (data.export_data) {
                    const dataStr = JSON.stringify(data.export_data, null, 2);
                    const dataBlob = new Blob([dataStr], {type: 'application/json'});
                    const url = URL.createObjectURL(dataBlob);
                    
                    const downloadLink = document.createElement('a');
                    downloadLink.href = url;
                    downloadLink.download = data.filename || 'kabu_data_export.json';
                    document.body.appendChild(downloadLink);
                    downloadLink.click();
                    document.body.removeChild(downloadLink);
                    
                    URL.revokeObjectURL(url);
                }
            } else {
                showAlert('エクスポートに失敗しました: ' + data.error, 'danger');
            }
        })
        .catch(error => {
            showAlert('エクスポート中にエラーが発生しました: ' + error.message, 'danger');
            console.error('Error:', error);
        });
}

/**
 * 数値フォーマット関数
 * @param {number} value - フォーマットする数値
 * @param {number} decimals - 小数点以下の桁数
 * @returns {string} フォーマットされた文字列
 */
function formatNumber(value, decimals = 0) {
    if (value === null || value === undefined || isNaN(value)) {
        return '-';
    }
    
    if (decimals > 0) {
        return parseFloat(value).toFixed(decimals);
    } else {
        return parseInt(value).toLocaleString();
    }
}

/**
 * 通貨フォーマット関数
 * @param {number} value - フォーマットする数値
 * @returns {string} フォーマットされた通貨文字列
 */
function formatCurrency(value) {
    if (value === null || value === undefined || isNaN(value)) {
        return '-';
    }
    return '¥' + parseInt(value).toLocaleString();
}

/**
 * パーセンテージフォーマット関数
 * @param {number} value - フォーマットする数値（0-1の範囲）
 * @param {number} decimals - 小数点以下の桁数
 * @returns {string} フォーマットされたパーセンテージ文字列
 */
function formatPercentage(value, decimals = 1) {
    if (value === null || value === undefined || isNaN(value)) {
        return '-';
    }
    return (value * 100).toFixed(decimals) + '%';
}

/**
 * 日付フォーマット関数
 * @param {string} dateString - フォーマットする日付文字列
 * @returns {string} フォーマットされた日付文字列
 */
function formatDate(dateString) {
    if (!dateString) return '-';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('ja-JP', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    } catch (error) {
        return dateString;
    }
}

/**
 * 株価の変化に応じたクラスを取得
 * @param {number} currentPrice - 現在価格
 * @param {number} previousPrice - 前回価格
 * @returns {string} CSSクラス名
 */
function getPriceChangeClass(currentPrice, previousPrice) {
    if (!currentPrice || !previousPrice) return 'price-neutral';
    
    if (currentPrice > previousPrice) return 'price-positive';
    if (currentPrice < previousPrice) return 'price-negative';
    return 'price-neutral';
}

/**
 * ローディング表示の制御
 * @param {string} elementId - 対象要素のID
 * @param {boolean} show - 表示するかどうか
 */
function toggleLoading(elementId, show) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (show) {
        element.classList.add('loading-overlay');
    } else {
        element.classList.remove('loading-overlay');
    }
}

/**
 * フォームデータを取得
 * @param {string} formId - フォームのID
 * @returns {Object} フォームデータのオブジェクト
 */
function getFormData(formId) {
    const form = document.getElementById(formId);
    if (!form) return {};
    
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    return data;
}

/**
 * フォームをリセット
 * @param {string} formId - フォームのID
 */
function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
    }
}

/**
 * テーブルの行をハイライト
 * @param {HTMLElement} row - 対象の行要素
 */
function highlightRow(row) {
    // 既存のハイライトを削除
    document.querySelectorAll('tr.table-warning').forEach(r => {
        r.classList.remove('table-warning');
    });
    
    // 新しい行をハイライト
    if (row) {
        row.classList.add('table-warning');
    }
}

/**
 * 検索キーワードをハイライト
 * @param {string} text - 対象テキスト
 * @param {string} keyword - 検索キーワード
 * @returns {string} ハイライト済みHTML
 */
function highlightSearchTerm(text, keyword) {
    if (!keyword || !text) return text;
    
    const regex = new RegExp(`(${keyword})`, 'gi');
    return text.replace(regex, '<span class="search-highlight">$1</span>');
}

/**
 * APIエラーハンドリング
 * @param {Response} response - fetch APIのレスポンス
 * @returns {Promise} 処理されたレスポンス
 */
async function handleApiResponse(response) {
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    return response.json();
}

/**
 * デバウンス関数
 * @param {Function} func - 実行する関数
 * @param {number} wait - 待機時間（ミリ秒）
 * @returns {Function} デバウンスされた関数
 */
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

/**
 * ローカルストレージにデータを保存
 * @param {string} key - キー
 * @param {any} data - 保存するデータ
 */
function saveToLocalStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
    } catch (error) {
        console.warn('Failed to save to localStorage:', error);
    }
}

/**
 * ローカルストレージからデータを取得
 * @param {string} key - キー
 * @param {any} defaultValue - デフォルト値
 * @returns {any} 取得したデータ
 */
function loadFromLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
        console.warn('Failed to load from localStorage:', error);
        return defaultValue;
    }
}

/**
 * CSVエクスポート関数
 * @param {Array} data - エクスポートするデータ配列
 * @param {string} filename - ファイル名
 */
function exportToCSV(data, filename = 'export.csv') {
    if (!data || data.length === 0) {
        showAlert('エクスポートするデータがありません。', 'warning');
        return;
    }
    
    // CSVヘッダーを作成
    const headers = Object.keys(data[0]);
    let csvContent = headers.join(',') + '\n';
    
    // データ行を追加
    data.forEach(row => {
        const values = headers.map(header => {
            let value = row[header] || '';
            // カンマやダブルクォートが含まれる場合の処理
            if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                value = '"' + value.replace(/"/g, '""') + '"';
            }
            return value;
        });
        csvContent += values.join(',') + '\n';
    });
    
    // ダウンロード
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * ページ読み込み完了時の共通初期化処理
 */
document.addEventListener('DOMContentLoaded', function() {
    // Bootstrap tooltipの初期化
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // 数値入力フィールドの改善
    document.querySelectorAll('input[type="number"]').forEach(input => {
        input.addEventListener('wheel', function(e) {
            e.preventDefault(); // マウスホイールでの値変更を防ぐ
        });
    });
    
    // フォームの改善
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = form.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                setTimeout(() => {
                    submitButton.disabled = false;
                }, 2000); // 2秒後に再有効化
            }
        });
    });
});

// エラーハンドリング
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
    showAlert('予期しないエラーが発生しました。ページを再読み込みしてください。', 'danger');
});

// 未処理のPromise拒否をキャッチ
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled Promise Rejection:', e.reason);
    showAlert('ネットワークエラーが発生しました。接続を確認してください。', 'warning');
});

// ユーティリティ関数のエクスポート（モジュール環境での使用に備えて）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        showAlert,
        formatNumber,
        formatCurrency,
        formatPercentage,
        formatDate,
        debounce,
        saveToLocalStorage,
        loadFromLocalStorage
    };
}
