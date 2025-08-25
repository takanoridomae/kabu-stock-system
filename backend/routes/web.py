"""
Webページルーティング（非API）
"""
from flask import Blueprint, render_template

# Webページ用ブループリント
web = Blueprint('web', __name__)


@web.route('/')
def index():
    """メインページ"""
    return render_template('index.html')


@web.route('/search')
def search():
    """検索ページ"""
    return render_template('search.html')


@web.route('/company-management')
def company_management():
    """企業管理ページ"""
    return render_template('company_management.html')