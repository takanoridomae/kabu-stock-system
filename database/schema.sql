-- 株式検索システム データベーススキーマ
-- 拡張性と正規化を考慮した設計

-- 企業情報テーブル
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(10) NOT NULL UNIQUE,  -- 株式コード
    name VARCHAR(255) NOT NULL,          -- 企業名
    sector VARCHAR(100),                 -- 業種
    market VARCHAR(50),                  -- 市場（東証一部、マザーズ等）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 株価履歴テーブル
CREATE TABLE IF NOT EXISTS stock_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    price DECIMAL(10,2) NOT NULL,        -- 株価
    price_date DATE NOT NULL,            -- 価格取得日
    volume BIGINT,                       -- 出来高
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, price_date)
);

-- 財務指標テーブル
CREATE TABLE IF NOT EXISTS financial_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    pbr DECIMAL(8,4),                    -- PBR（株価純資産倍率）
    per DECIMAL(8,4),                    -- PER（株価収益率）
    equity_ratio DECIMAL(8,4),           -- 自己資本比率
    roe DECIMAL(8,4),                    -- ROE（自己資本利益率）
    roa DECIMAL(8,4),                    -- ROA（総資産利益率）
    report_date DATE NOT NULL,           -- 財務報告日
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, report_date)
);

-- 価格統計テーブル（月間、年間、過去最高/最低）
CREATE TABLE IF NOT EXISTS price_statistics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    period_type VARCHAR(20) NOT NULL,    -- 'monthly', 'yearly', 'all_time'
    period_value VARCHAR(20) NOT NULL,   -- 'YYYY-MM' for monthly, 'YYYY' for yearly, 'all' for all_time
    min_price DECIMAL(10,2),             -- 最低価格
    max_price DECIMAL(10,2),             -- 最高価格
    avg_price DECIMAL(10,2),             -- 平均価格
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, period_type, period_value)
);

-- テクニカル指標テーブル
CREATE TABLE IF NOT EXISTS technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    indicator_date DATE NOT NULL,
    rsi DECIMAL(8,4),                    -- RSI
    macd DECIMAL(8,4),                   -- MACD
    sma_25 DECIMAL(10,2),                -- 25日移動平均
    sma_75 DECIMAL(10,2),                -- 75日移動平均
    bollinger_upper DECIMAL(10,2),       -- ボリンジャーバンド上限
    bollinger_lower DECIMAL(10,2),       -- ボリンジャーバンド下限
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, indicator_date)
);

-- インデックス作成（パフォーマンス向上）
CREATE INDEX IF NOT EXISTS idx_companies_symbol ON companies(symbol);
CREATE INDEX IF NOT EXISTS idx_stock_prices_company_date ON stock_prices(company_id, price_date DESC);
CREATE INDEX IF NOT EXISTS idx_financial_metrics_company_date ON financial_metrics(company_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_price_statistics_company_period ON price_statistics(company_id, period_type, period_value);
CREATE INDEX IF NOT EXISTS idx_technical_indicators_company_date ON technical_indicators(company_id, indicator_date DESC);

-- トリガー：updated_atの自動更新
CREATE TRIGGER IF NOT EXISTS update_companies_updated_at 
    AFTER UPDATE ON companies
    FOR EACH ROW
    BEGIN
        UPDATE companies SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER IF NOT EXISTS update_price_statistics_updated_at 
    AFTER UPDATE ON price_statistics
    FOR EACH ROW
    BEGIN
        UPDATE price_statistics SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- サンプルデータ（開発・テスト用）
INSERT OR IGNORE INTO companies (symbol, name, sector, market) VALUES
('7203', 'トヨタ自動車', '輸送用機器', '東証プライム'),
('6758', 'ソニーグループ', '電気機器', '東証プライム'),
('9984', 'ソフトバンクグループ', '情報・通信業', '東証プライム'),
('6861', 'キーエンス', '電気機器', '東証プライム'),
('4519', '中外製薬', '医薬品', '東証プライム');
