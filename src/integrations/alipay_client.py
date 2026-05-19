"""支付宝开放平台客户端"""
import os
import logging
from typing import Optional, Dict
from datetime import datetime
from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayDataDataserviceBillDownloadurlQueryModel import AlipayDataDataserviceBillDownloadurlQueryModel
from alipay.aop.api.request.AlipayDataDataserviceBillDownloadurlQueryRequest import AlipayDataDataserviceBillDownloadurlQueryRequest
from alipay.aop.api.request.AlipaySystemOauthTokenRequest import AlipaySystemOauthTokenRequest

logger = logging.getLogger(__name__)

class AlipayClient:
    """支付宝API客户端"""

    def __init__(self):
        """初始化客户端"""
        self._init_client()

    def _init_client(self):
        """初始化SDK客户端"""
        app_id = os.getenv('ALIPAY_APP_ID')
        private_key = os.getenv('ALIPAY_PRIVATE_KEY')
        public_key = os.getenv('ALIPAY_PUBLIC_KEY')

        self.app_id = app_id  # Store app_id for later use

        if not all([app_id, private_key, public_key]):
            logger.warning("支付宝API配置不完整，API功能将不可用")
            self.client = None
            return

        config = AlipayClientConfig()
        config.app_id = app_id
        config.app_private_key = private_key
        config.alipay_public_key = public_key
        config.sign_type = 'RSA2'
        config.debug = os.getenv('APP_ENV') == 'development'
        
        if config.debug:
            config.server_url = 'https://openapi.alipaydev.com/gateway.do'
        else:
            config.server_url = 'https://openapi.alipay.com/gateway.do'

        self.client = DefaultAlipayClient(alipay_client_config=config)

    def get_oauth_url(self, redirect_uri: str) -> str:
        """
        获取授权URL
        
        Args:
            redirect_uri: 回调地址
            
        Returns:
            授权URL
        """
        if not self.client or not self.app_id:
            return ""
            
        # 构造授权URL
        # 商家应用授权 scope=alipay.user.info (获取用户信息) 或其他权限
        # 注意：账单下载通常是代商户调用，需要商户授权给ISV，或者商户自己调用
        # 这里假设是商户自己使用，或者简单的第三方应用授权
        base_url = "https://openauth.alipaydev.com/oauth2/publicAppAuthorize.htm" if os.getenv('APP_ENV') == 'development' else "https://openauth.alipay.com/oauth2/publicAppAuthorize.htm"
        
        from urllib.parse import quote
        encoded_uri = quote(redirect_uri)
        return f"{base_url}?app_id={self.app_id}&scope=auth_base&redirect_uri={encoded_uri}"

    def get_access_token(self, auth_code: str) -> Optional[Dict]:
        """
        使用auth_code换取access_token
        
        Args:
            auth_code: 授权码
            
        Returns:
            Token信息
        """
        if not self.client:
            return None

        request = AlipaySystemOauthTokenRequest()
        request.grant_type = "authorization_code"
        request.code = auth_code
        
        try:
            response = self.client.execute(request)
            if response.get('access_token'):
                return {
                    'access_token': response.get('access_token'),
                    'user_id': response.get('user_id'),
                    'expires_in': response.get('expires_in'),
                    're_expires_in': response.get('re_expires_in'),
                    'refresh_token': response.get('refresh_token')
                }
            else:
                logger.error(f"获取Token失败: {response.get('sub_msg')}")
                return None
        except Exception as e:
            logger.error(f"获取Token异常: {str(e)}")
            return None

    def query_bill_download_url(self, bill_type: str, date: str, token: Optional[str] = None) -> Optional[str]:
        """
        查询账单下载地址
        
        Args:
            bill_type: 账单类型 (trade/signcustomer/...)
            date: 账单日期 (YYYY-MM or YYYY-MM-DD)
            token: 应用授权令牌 (如果是代商户调用)
            
        Returns:
            下载地址
        """
        if not self.client:
            return None

        model = AlipayDataDataserviceBillDownloadurlQueryModel()
        model.bill_type = bill_type
        model.bill_date = date
        
        request = AlipayDataDataserviceBillDownloadurlQueryRequest(biz_model=model)
        
        # 如果提供了token (ISV模式)，则传入
        # 如果是自用型应用，不需要token，直接使用app_id签名即可
        
        try:
            response = self.client.execute(request, app_auth_token=token)
            if response.get('bill_download_url'):
                return response.get('bill_download_url')
            else:
                logger.error(f"获取账单地址失败: {response.get('sub_msg')}")
                return None
        except Exception as e:
            logger.error(f"获取账单地址异常: {str(e)}")
            return None
