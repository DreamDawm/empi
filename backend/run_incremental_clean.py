#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增量清洗脚本 - 直接运行，不通过API接口

使用方法:
    cd backend
    python run_incremental_clean.py [--batch-size SIZE]

参数:
    --batch-size: 每批处理数量，默认3000
"""

import argparse
import sys
import os
import io

# 设置标准输出编码为UTF-8（解决Windows终端中文乱码）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.base import SessionLocal
from app.services.etl import etl_scheduler
from app.services.logging_service import logging_service


def run_incremental_clean(batch_size: int = 3000):
    """运行增量清洗"""
    db = SessionLocal()

    try:
        logging_service.info(f"开始增量清洗，batch_size={batch_size}")

        total_stats = {'processed': 0, 'merged': 0, 'pending': 0}
        round_num = 0

        while True:
            round_num += 1
            logging_service.info(f"\n{'='*50}")
            logging_service.info(f"第 {round_num} 轮清洗开始")
            logging_service.info(f"{'='*50}")

            stats = etl_scheduler.poll_and_process(db, batch_size=batch_size)

            total_stats['processed'] += stats['processed']
            total_stats['merged'] += stats['merged']
            total_stats['pending'] += stats['pending']

            logging_service.info(f"第 {round_num} 轮完成: 处理={stats['processed']}, 合并={stats['merged']}, 待审核={stats['pending']}")
            logging_service.info(f"累计统计: 处理={total_stats['processed']}, 合并={total_stats['merged']}, 待审核={total_stats['pending']}")

            if stats['processed'] == 0:
                logging_service.info("\n增量清洗完成!")
                logging_service.info(f"最终统计: 处理={total_stats['processed']}, 合并={total_stats['merged']}, 待审核={total_stats['pending']}")
                break

    except Exception as e:
        logging_service.error(f"增量清洗出错: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='运行增量清洗任务')
    parser.add_argument('--batch-size', type=int, default=3000, help='每批处理数量')
    args = parser.parse_args()

    run_incremental_clean(batch_size=args.batch_size)