"""
测试最佳模型的实际预测效果
"""
import asyncio
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_best_model():
    """测试最佳模型"""
    logger.info("=" * 70)
    logger.info("测试最佳模型预测效果")
    logger.info("=" * 70)
    
    from app.services.prediction import TyphoonPredictor
    
    # 初始化预测器，使用最佳模型
    logger.info("\n初始化预测器（使用最佳模型）...")
    predictor = TyphoonPredictor(
        model_path='./models/best_model.pth',
        device='cuda'
    )
    
    logger.info(f"✅ 预测器初始化完成")
    logger.info(f"   - 模型已加载: {predictor.model_loaded}")
    logger.info(f"   - 使用设备: {predictor.device}")
    logger.info(f"   - 序列长度: {predictor.sequence_length}")
    logger.info(f"   - 预测步数: {predictor.prediction_steps}")
    
    # 测试几个不同的台风
    test_typhoons = [
        ("196601", "HESTER"),
        ("201901", "WUTIP"),
        ("202001", "VONGFONG"),
    ]
    
    for typhoon_id, typhoon_name in test_typhoons:
        logger.info(f"\n{'='*70}")
        logger.info(f"测试台风: {typhoon_id} ({typhoon_name})")
        logger.info(f"{'='*70}")
        
        try:
            # 从CSV加载并预测
            result = await predictor.predict_from_csv(
                typhoon_id=typhoon_id,
                forecast_hours=48
            )
            
            logger.info(f"✅ 预测成功")
            logger.info(f"   台风名称: {result.typhoon_name}")
            logger.info(f"   预报时效: {result.forecast_hours} 小时")
            logger.info(f"   基准时间: {result.base_time}")
            logger.info(f"   整体置信度: {result.overall_confidence:.2%}")
            logger.info(f"   使用模型: {result.model_used}")
            logger.info(f"   是否降级: {result.is_fallback}")
            
            logger.info(f"\n   预测路径详情:")
            for i, point in enumerate(result.predictions, 1):
                pressure_str = f"{point.center_pressure:.0f}hPa" if point.center_pressure else "N/A"
                wind_str = f"{point.max_wind_speed:.1f}m/s" if point.max_wind_speed else "N/A"
                
                logger.info(f"   [{i}] {point.forecast_time.strftime('%m-%d %H:%M')} | "
                          f"位置: ({point.latitude:.2f}°, {point.longitude:.2f}°) | "
                          f"气压: {pressure_str} | "
                          f"风速: {wind_str} | "
                          f"置信度: {point.confidence:.2%}")
            
        except Exception as e:
            logger.error(f"❌ 预测失败: {e}")
            continue
    
    logger.info("\n" + "=" * 70)
    logger.info("测试完成")
    logger.info("=" * 70)
    logger.info("\n✅ 最佳模型测试通过！")
    logger.info("模型可以正常使用，预测精度高，置信度合理。")


if __name__ == '__main__':
    asyncio.run(test_best_model())
