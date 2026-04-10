from typing import List, Any, Dict
import sys
from pathlib import Path
import math

# 将项目根目录加入 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from app.fid.validators.base_rules import BaseRule
from app.fid.models import CheckResult
from app.fid.utils.parse_block_attributes import parse_block_attributes
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.expand_frame_repr', False)


class BlockPositionCheck(BaseRule):
    rule_type = "warning"
    rule_name = '图块位置变更'
    DEFAULT_FIELDS = ["cad_block_name", "layer", "insert_point_x", "insert_point_y", "insert_point_z", "angle",
                      "true_color", "cad_block_id", "distribution_box"]

    def check(self, equipments: Dict[str, List[Dict[str, Any]]], device: str = None, request_data=None) -> List[
        CheckResult]:
        """
        对所有 equipment 执行位置校验。
        """
        if device is not None:
            equipments = equipments.get(device, [])

        if len(equipments) == 0:
            return []

        results = []

        # --- 1. 数据准备与预处理 (关键优化点) ---
        interface_pd = pd.DataFrame.from_dict(request_data['interface_list']).add_prefix('INTERFACE.')
        field_pd = pd.DataFrame.from_dict(request_data['field_list']).add_prefix('FIELD.')

        if interface_pd.empty:
            interface_pd = pd.DataFrame([], columns=['id', 'field_id', 'uni_code', 'cad_block_id', 'insert_point_x',
                                                     'insert_point_y', 'insert_point_z']).add_prefix('INTERFACE.')

        # 修复原代码中列定义缺少逗号的问题
        if field_pd.empty:
            field_pd = pd.DataFrame([], columns=['id', 'system_id', 'subsystem_id',
                                                 'code', 'uni_code', 'cad_block_id',
                                                 'insert_point_x', 'insert_point_y', 'insert_point_z']).add_prefix(
                'FIELD.')

        final_df = pd.merge(
            field_pd,
            interface_pd,
            left_on='FIELD.id',
            right_on='INTERFACE.field_id',
            how='left'
        )

        # 【核心优化】：构建查找字典
        # 将 DataFrame 转换为 { uni_code: row_dict }
        # 这样在循环中查找只需要 O(1) 时间，而不是 O(N)
        lookup_dict = {}
        if not final_df.empty:
            required_cols = ['INTERFACE.insert_point_x', 'INTERFACE.insert_point_y', 'INTERFACE.insert_point_z']

            # 确保坐标列存在，避免后续报错
            for col in required_cols:
                if col not in final_df.columns:
                    final_df[col] = 0.0

            # 步骤 A: 过滤掉 uni_code 为 NaN/None 的行 (这些行无法作为字典键)
            valid_df = final_df[final_df['INTERFACE.uni_code'].notna()]

            if not valid_df.empty:
                # 步骤 B: 去重。如果有重复的 uni_code，保留最后一条 (keep='last')
                # 这解决了 "DataFrame index must be unique" 的错误
                deduped_df = valid_df.drop_duplicates(subset=['INTERFACE.uni_code'], keep='last')

                # 步骤 C: 构建字典
                # 此时索引保证唯一且非空
                try:
                    # 只提取需要的坐标列转换为字典，减少内存占用
                    # orient='index' 会生成 { uni_code: { col: val, ... } }
                    lookup_dict = deduped_df.set_index('INTERFACE.uni_code')[required_cols].to_dict(orient='index')
                except ValueError as e:
                    print(f"[ERROR] 构建位置查找字典失败：{e}。跳过位置检查。")
                    lookup_dict = {}




        threshold = 0.1  # 统一阈值

        # --- 2. 主循环 ---
        for eq in equipments:
            equipments_info = parse_block_attributes(eq, request_data['filename'])

            if not equipments_info:
                continue

            description = ""
            for info in equipments_info:

                uni_code = info.get('interface_code')

                # 【核心优化】：直接从字典获取数据，无需遍历 DataFrame
                target_data = lookup_dict.get(uni_code)

                if target_data is None:
                    continue

                # 安全获取坐标值 (处理 NaN 或 None)
                def get_coord(val):
                    if val is None:
                        return 0.0
                    try:
                        f_val = float(val)
                        return 0.0 if math.isnan(f_val) else f_val
                    except (ValueError, TypeError):
                        return 0.0

                old_x = get_coord(target_data.get('INTERFACE.insert_point_x'))
                old_y = get_coord(target_data.get('INTERFACE.insert_point_y'))
                old_z = get_coord(target_data.get('INTERFACE.insert_point_z'))

                new_x = get_coord(info.get('insert_point_x'))
                new_y = get_coord(info.get('insert_point_y'))
                new_z = get_coord(info.get('insert_point_z'))

                # 计算差值
                dx = abs(old_x - new_x)
                dy = abs(old_y - new_y)
                dz = abs(old_z - new_z)

                # 判断是否超过阈值
                #if dx >= threshold or dy >= threshold or dz >= threshold:
                if dx >= threshold:
                    description += f"insert_point_x({old_x},{new_x})\n"
                if dy >= threshold:
                    description += f"insert_point_y({old_y},{new_y})\n"
                if dz >= threshold:
                    description += f"insert_point_z({old_z},{new_z})\n"

                if len(description) > 0:
                    results.append(CheckResult(
                        type=self.rule_type,
                        name="图块位置变更",
                        description=description,
                        detail=f"坐标偏移量：dx={dx:.4f}, dy={dy:.4f}, dz={dz:.4f} (阈值:{threshold})",
                        equipment=[eq],
                        operation='update',
                        field_or_interface='field',
                        device=device
                    ))
                    break
        return results


if __name__ == '__main__':
    pass
