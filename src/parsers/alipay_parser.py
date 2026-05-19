"""支付宝账单解析器"""
import pandas as pd
from typing import Dict
from .base_parser import BaseParser


class AlipayParser(BaseParser):
    """支付宝账单解析器"""

    PLATFORM_NAME = "alipay"

    def parse(self, file_path: str) -> pd.DataFrame:
        """
        解析支付宝账单文件 (支持个人CSV和商户XLS/CSV)

        Args:
            file_path: 账单文件路径

        Returns:
            标准化后的DataFrame
        """
        # 检测是否为商户账单 (.xls/.xlsx)
        if file_path.lower().endswith(('.xls', '.xlsx')):
            return self._parse_merchant_bill(file_path)
        
        # 检测是否为商户账单 (CSV)
        # 有些用户可能将xls另存为csv，或者直接上传csv格式的商户账单
        if self._is_merchant_csv(file_path):
            return self._parse_merchant_csv(file_path)
        
        # 默认处理个人账单 (CSV)
        return self._parse_personal_bill(file_path)

    def _parse_personal_bill(self, file_path: str) -> pd.DataFrame:
        """解析个人账单CSV"""
        # 1. 确定编码和表头行
        # 用户反馈可能需要utf-8，但实际文件可能是gbk，所以都尝试
        encodings = ['utf-8', 'gbk', 'gb18030']
        header_row_index = None
        selected_encoding = None

        for enc in encodings:
            try:
                # 使用 errors='ignore' 避免因少量乱码导致检测失败
                with open(file_path, 'r', encoding=enc, errors='ignore') as f:
                    for i, line in enumerate(f):
                        # 检查关键列名
                        # 常见列名：交易时间, 交易创建时间, 交易号, 交易对方, 商品说明, 商品名称
                        if (('交易时间' in line or '交易创建时间' in line) and 
                            ('交易对方' in line or '商品说明' in line or '商品名称' in line)):
                            header_row_index = i
                            selected_encoding = enc
                            break
                if header_row_index is not None:
                    break
            except Exception:
                continue

        if header_row_index is None:
            # 如果没找到表头，尝试默认读取，优先尝试GBK (支付宝默认)
            selected_encoding = 'gbk'
            header_row_index = 0
            
        # 2. 读取数据
        df = None
        # 尝试的编码列表：优先使用检测到的，然后是GBK，然后是UTF-8
        try_encodings = [selected_encoding]
        if 'gbk' not in try_encodings: try_encodings.append('gbk')
        if 'utf-8' not in try_encodings: try_encodings.append('utf-8')
        if 'gb18030' not in try_encodings: try_encodings.append('gb18030')
        
        last_error = None
        for enc in try_encodings:
            try:
                # 显式指定分隔符为逗号，防止自动检测失败
                df = pd.read_csv(file_path, encoding=enc, skiprows=header_row_index, sep=',')
                break
            except Exception as e:
                last_error = e
                # 尝试 python 引擎
                try:
                    df = pd.read_csv(file_path, encoding=enc, skiprows=header_row_index, engine='python', sep=',')
                    break
                except Exception as e2:
                    continue
        
        if df is None:
            raise last_error or ValueError("无法读取CSV文件")

        # 清理列名空格
        df.columns = df.columns.str.strip()
        
        # 清理数据值空格
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].str.strip()

        # 3. 清理和标准化
        # 移除空行和页脚
        # 确保包含必要列
        if '交易时间' in df.columns:
            df = df.dropna(subset=['交易时间'])
        
        # 标准化字段
        df_standard = self.standardize(df)

        # 过滤排除的交易类型
        df_standard = self._filter_excluded_transactions(df_standard)

        # 验证数据
        self.validate_data(df_standard)

        return df_standard

    def _is_merchant_csv(self, file_path: str) -> bool:
        """检测是否为商户CSV账单"""
        try:
            # 读取前几行文本
            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                head = [next(f) for _ in range(5)]
            content = ''.join(head)
            
            # 商户账单特征
            return '账单编号' in content and '服务提供方' in content and '应收总额' in content
        except:
            return False

    def _parse_merchant_csv(self, file_path: str) -> pd.DataFrame:
        """解析商户账单CSV"""
        try:
            # 读取CSV文件
            df = None
            encodings = ['utf-8', 'gbk', 'gb18030']
            for enc in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=enc)
                    break
                except:
                    continue
            
            if df is None:
                raise ValueError("无法读取CSV文件，编码不支持")

            return self._process_merchant_df(df)
        except Exception as e:
            raise ValueError(f"解析商户CSV账单失败: {str(e)}")

    def _parse_merchant_bill(self, file_path: str) -> pd.DataFrame:
        """解析商户账单XLS"""
        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            return self._process_merchant_df(df)
        except Exception as e:
            raise ValueError(f"解析商户账单失败: {str(e)}")

    def _process_merchant_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理商户账单DataFrame (通用逻辑)"""
        # 构造标准DataFrame
        records = []
        for _, row in df.iterrows():
            # 处理日期：商户账单只有"月份" (e.g. "2023-10" or similar), 默认为该月1号
            # 注意：实际sample可能需要根据内容调整
            bill_month = str(row.get('月份', ''))
            try:
                date_obj = pd.to_datetime(bill_month)
            except:
                date_obj = pd.Timestamp.now() # Fallback

            # 金额：优先使用实收总额，如果没有则用应收
            amount = row.get('实收总额', 0)
            if pd.isna(amount):
                amount = row.get('应收总额', 0)
            
            # 交易类型：商户结算单通常是收入(income)或费用(expense)
            # 这里假设是结算收入，如果是服务费则是支出。
            # 简单起见，正数为income
            trans_type = 'income'
            
            record = {
                'transaction_id': str(row.get('账单编号', '')),
                'date': date_obj,
                'category': row.get('费用名称', '商户结算'),
                'counterparty': row.get('服务提供方', '支付宝'),
                'description': f"商户结算单 - {row.get('费用名称', '')}",
                'amount': float(amount) if amount else 0.0,
                'type': trans_type,
                'platform': self.PLATFORM_NAME,
                'status': 'completed' # 默认为完成
            }
            records.append(record)
        
        df_standard = pd.DataFrame(records)
        
        # 如果为空，确保有必要的列
        if df_standard.empty:
            columns = [
                'transaction_id', 'date', 'category', 'counterparty', 
                'description', 'amount', 'type', 'platform', 'status'
            ]
            df_standard = pd.DataFrame(columns=columns)
        
        # 生成ID如果缺失
        if 'transaction_id' not in df_standard.columns or df_standard['transaction_id'].isna().all():
            df_standard['transaction_id'] = self._generate_transaction_id(df_standard)

        return df_standard

    def detect_format(self, file_path: str) -> bool:
        """
        检测是否为支付宝账单格式
        """
        try:
            # 1. 检查扩展名 (.xls/.xlsx)
            if file_path.lower().endswith(('.xls', '.xlsx')):
                df = pd.read_excel(file_path, nrows=5)
                merchant_cols = ['账单编号', '服务提供方', '应收总额']
                if any(col in df.columns for col in merchant_cols):
                    return True
                return False

            # 2. 检查CSV (文本检测)
            with open(file_path, 'r', encoding='gbk', errors='ignore') as f:
                head = [next(f) for _ in range(10)]
            content = ''.join(head)
            
            # 个人账单特征
            if '支付宝交易记录明细查询' in content or ('交易时间' in content and '交易对方' in content):
                return True
                
            # 商户账单特征
            if '账单编号' in content and '服务提供方' in content:
                return True
                
            return False

        except Exception:
            return False

    def _clean_alipay_header(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        清理支付宝CSV头部信息 (已在读取时处理，此方法保留兼容性)
        """
        return df

    def _filter_excluded_transactions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        过滤排除的交易类型
        """
        return df

    def _merge_time_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        合并日期和时间列
        """
        if 'date' in df.columns and 'time' in df.columns:
            df['date'] = pd.to_datetime(
                df['date'].astype(str) + ' ' + df['time'].astype(str)
            )
            df = df.drop(columns=['time'])
        
        return df
