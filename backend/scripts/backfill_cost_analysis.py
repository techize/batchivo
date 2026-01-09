"""Backfill cost analysis for existing completed production runs.

This script calculates cost_per_gram_actual, successful_weight_grams,
model_weight_grams, and actual_cost_per_unit for completed runs that
don't have this data yet.
"""

import asyncio
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.database import async_session_maker
from app.models.production_run import ProductionRun
from app.models.model_material import ModelMaterial


async def get_model_weight(db, model_id) -> Decimal:
    """Get total material weight for a model from its BOM."""
    result = await db.execute(
        select(func.sum(ModelMaterial.weight_grams)).where(ModelMaterial.model_id == model_id)
    )
    total_weight = result.scalar()
    return Decimal(str(total_weight)) if total_weight else Decimal("0")


async def backfill_run(db, run: ProductionRun) -> bool:
    """Backfill cost analysis for a single run. Returns True if updated."""
    # Calculate total material cost
    total_material_cost = Decimal("0")
    for material in run.materials:
        if material.cost_per_gram and material.actual_total_weight:
            total_material_cost += Decimal(str(material.actual_total_weight)) * Decimal(
                str(material.cost_per_gram)
            )

    if total_material_cost == 0:
        print(f"  Skipping {run.run_number}: no material cost data")
        return False

    successful_weight = Decimal("0")

    # Handle multi-plate runs
    if run.is_multi_plate and run.plates:
        for plate in run.plates:
            if plate.successful_prints and plate.successful_prints > 0:
                model_weight = await get_model_weight(db, plate.model_id)
                plate.model_weight_grams = model_weight
                successful_weight += Decimal(str(plate.successful_prints)) * model_weight

    # Handle legacy item-based runs
    elif run.items:
        for item in run.items:
            if item.successful_quantity and item.successful_quantity > 0:
                model_weight = await get_model_weight(db, item.model_id)
                item.model_weight_grams = model_weight
                successful_weight += Decimal(str(item.successful_quantity)) * model_weight

    if successful_weight == 0:
        print(f"  Skipping {run.run_number}: no successful items/plates")
        return False

    # Calculate cost per gram
    cost_per_gram = total_material_cost / successful_weight
    run.cost_per_gram_actual = cost_per_gram
    run.successful_weight_grams = successful_weight

    # Calculate per-item/plate costs
    if run.is_multi_plate and run.plates:
        for plate in run.plates:
            if plate.model_weight_grams:
                plate.actual_cost_per_unit = plate.model_weight_grams * cost_per_gram
    elif run.items:
        for item in run.items:
            if item.model_weight_grams:
                item.actual_cost_per_unit = item.model_weight_grams * cost_per_gram

    print(
        f"  Updated {run.run_number}: cost_per_gram={cost_per_gram:.4f}, successful_weight={successful_weight}g"
    )
    return True


async def main():
    """Main backfill function."""
    print("Starting cost analysis backfill...")

    async with async_session_maker() as db:
        # Find completed runs without cost analysis
        result = await db.execute(
            select(ProductionRun)
            .options(
                selectinload(ProductionRun.items),
                selectinload(ProductionRun.materials),
                selectinload(ProductionRun.plates),
            )
            .where(
                and_(
                    ProductionRun.status == "completed",
                    ProductionRun.cost_per_gram_actual.is_(None),
                )
            )
            .order_by(ProductionRun.completed_at.desc())
        )
        runs = result.scalars().all()

        print(f"Found {len(runs)} completed runs without cost analysis")

        updated_count = 0
        for run in runs:
            try:
                if await backfill_run(db, run):
                    updated_count += 1
            except Exception as e:
                print(f"  Error processing {run.run_number}: {e}")

        await db.commit()
        print(f"\nBackfill complete: {updated_count} runs updated")


if __name__ == "__main__":
    asyncio.run(main())
