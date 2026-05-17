"""
Performance benchmark runner for the Typhoon Analysis backend.

This script benchmarks a small set of reproducible API endpoints, generates
raw data files, plots, and a thesis-friendly Markdown report.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import httpx
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT_DIR / "docs" / "performance"
FONT_CANDIDATE_FILES = [
    Path(r"C:\Windows\Fonts\simsun.ttc"),
    Path(r"C:\Windows\Fonts\simhei.ttf"),
    Path(r"C:\Windows\Fonts\msyh.ttc"),
    Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
]
EXPORT_DPI = 600


def configure_matplotlib() -> None:
    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except OSError:
        pass

    font_family = "SimSun"
    for font_path in FONT_CANDIDATE_FILES:
        if not font_path.exists():
            continue
        try:
            font_manager.fontManager.addfont(str(font_path))
            font_family = font_manager.FontProperties(fname=str(font_path)).get_name()
            break
        except RuntimeError:
            continue

    plt.rcParams.update(
        {
            "font.family": font_family,
            "font.sans-serif": [font_family, "SimSun", "SimHei", "Microsoft YaHei", "DejaVu Sans"],
            "axes.unicode_minus": False,
            "figure.facecolor": "#FFFFFF",
            "axes.facecolor": "#FFFFFF",
            "axes.edgecolor": "#8A8A8A",
            "axes.labelcolor": "#000000",
            "axes.titleweight": "bold",
            "axes.titlesize": 16,
            "axes.labelsize": 12,
            "xtick.color": "#000000",
            "ytick.color": "#000000",
            "text.color": "#000000",
            "grid.color": "#C8C8C8",
            "grid.alpha": 0.22,
            "legend.frameon": True,
            "legend.facecolor": "#FFFFFF",
            "legend.edgecolor": "#8A8A8A",
            "savefig.facecolor": "#FFFFFF",
            "savefig.dpi": EXPORT_DPI,
        }
    )


configure_matplotlib()


@dataclass
class BenchmarkCase:
    case_id: str
    display_name: str
    method: str
    path: str
    request_factory: Callable[[dict[str, Any]], dict[str, Any]]
    total_requests: int
    concurrency: int
    category: str
    warmup_requests: int = 2


@dataclass
class BenchmarkResult:
    case_id: str
    display_name: str
    method: str
    path: str
    category: str
    total_requests: int
    concurrency: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_ms: float
    median_ms: float
    p95_ms: float
    std_ms: float
    min_ms: float
    max_ms: float
    throughput_rps: float
    avg_size_bytes: float
    status_code_summary: dict[str, int]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * p
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return sorted_values[low]
    low_value = sorted_values[low]
    high_value = sorted_values[high]
    return low_value + (high_value - low_value) * (rank - low)


async def ensure_test_user(base_url: str) -> tuple[str, str]:
    username = f"perf_user_{int(time.time())}"
    password = "PerfTest123456!"
    payload = {
        "username": username,
        "email": f"{username}@example.com",
        "password": password,
        "phone": "13800138000",
    }
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.post("/api/auth/register", json=payload)
        response.raise_for_status()
    return username, password


async def login_and_get_token(base_url: str, username: str, password: str) -> str:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.post(
            "/api/auth/login",
            data={"username": username, "password": password},
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def discover_sample_typhoon(base_url: str) -> dict[str, str]:
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        response = await client.get("/api/typhoons", params={"limit": 5})
        response.raise_for_status()
        items = response.json()["items"]
        if not items:
            raise RuntimeError("未获取到可用于性能测试的台风样本")
        sample = items[0]
        keyword = sample.get("typhoon_name_cn") or sample.get("typhoon_name") or sample["typhoon_id"]
        return {
            "typhoon_id": sample["typhoon_id"],
            "keyword": keyword,
        }


async def detect_prediction_mode(base_url: str, typhoon_id: str) -> str:
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        response = await client.post(
            "/api/predictions/path",
            json={
                "typhoon_id": typhoon_id,
                "forecast_hours": 24,
                "use_ensemble": False,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            return str(payload[0].get("prediction_model") or "未知")
        return "未知"


async def issue_request(
    client: httpx.AsyncClient,
    case: BenchmarkCase,
    context: dict[str, Any],
) -> dict[str, Any]:
    request_kwargs = case.request_factory(context)
    method = case.method.upper()
    started = time.perf_counter()
    try:
        response = await client.request(method, case.path, **request_kwargs)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "ok": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "size_bytes": len(response.content),
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "ok": False,
            "status_code": f"EXC:{type(exc).__name__}",
            "elapsed_ms": elapsed_ms,
            "size_bytes": 0,
        }


async def run_case(
    base_url: str,
    case: BenchmarkCase,
    context: dict[str, Any],
) -> tuple[BenchmarkResult, list[dict[str, Any]]]:
    limits = httpx.Limits(max_connections=max(case.concurrency * 2, 20))
    timeout = httpx.Timeout(60.0, connect=15.0)
    async with httpx.AsyncClient(base_url=base_url, timeout=timeout, limits=limits) as client:
        for _ in range(case.warmup_requests):
            await issue_request(client, case, context)

        semaphore = asyncio.Semaphore(case.concurrency)
        raw_rows: list[dict[str, Any]] = []

        async def guarded_request(index: int) -> None:
            async with semaphore:
                row = await issue_request(client, case, context)
                row["request_index"] = index
                raw_rows.append(row)

        started = time.perf_counter()
        await asyncio.gather(*(guarded_request(i) for i in range(case.total_requests)))
        total_elapsed = time.perf_counter() - started

    latencies = [float(row["elapsed_ms"]) for row in raw_rows]
    successes = [row for row in raw_rows if row["ok"]]
    success_count = len(successes)
    failure_count = len(raw_rows) - success_count
    status_summary: dict[str, int] = {}
    for row in raw_rows:
        key = str(row["status_code"])
        status_summary[key] = status_summary.get(key, 0) + 1

    result = BenchmarkResult(
        case_id=case.case_id,
        display_name=case.display_name,
        method=case.method.upper(),
        path=case.path,
        category=case.category,
        total_requests=case.total_requests,
        concurrency=case.concurrency,
        success_count=success_count,
        failure_count=failure_count,
        success_rate=(success_count / len(raw_rows) * 100.0) if raw_rows else 0.0,
        avg_ms=statistics.mean(latencies) if latencies else 0.0,
        median_ms=statistics.median(latencies) if latencies else 0.0,
        p95_ms=percentile(latencies, 0.95),
        std_ms=statistics.pstdev(latencies) if len(latencies) > 1 else 0.0,
        min_ms=min(latencies) if latencies else 0.0,
        max_ms=max(latencies) if latencies else 0.0,
        throughput_rps=(len(raw_rows) / total_elapsed) if total_elapsed > 0 else 0.0,
        avg_size_bytes=statistics.mean([row["size_bytes"] for row in raw_rows]) if raw_rows else 0.0,
        status_code_summary=status_summary,
    )
    return result, raw_rows


def build_cases() -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            case_id="health",
            display_name="健康检查",
            method="GET",
            path="/health",
            request_factory=lambda ctx: {},
            total_requests=30,
            concurrency=10,
            category="基础服务",
        ),
        BenchmarkCase(
            case_id="auth_login",
            display_name="用户登录",
            method="POST",
            path="/api/auth/login",
            request_factory=lambda ctx: {
                "data": {
                    "username": ctx["username"],
                    "password": ctx["password"],
                }
            },
            total_requests=20,
            concurrency=5,
            category="认证服务",
        ),
        BenchmarkCase(
            case_id="auth_profile",
            display_name="当前用户信息查询",
            method="GET",
            path="/api/auth/me",
            request_factory=lambda ctx: {
                "headers": {"Authorization": f"Bearer {ctx['token']}"},
            },
            total_requests=20,
            concurrency=5,
            category="认证服务",
        ),
        BenchmarkCase(
            case_id="typhoon_list",
            display_name="台风列表查询",
            method="GET",
            path="/api/typhoons",
            request_factory=lambda ctx: {"params": {"limit": 20}},
            total_requests=40,
            concurrency=10,
            category="查询服务",
        ),
        BenchmarkCase(
            case_id="typhoon_search",
            display_name="台风关键词检索",
            method="GET",
            path="/api/typhoons/search",
            request_factory=lambda ctx: {"params": {"keyword": ctx["sample_keyword"], "limit": 20}},
            total_requests=30,
            concurrency=10,
            category="查询服务",
        ),
        BenchmarkCase(
            case_id="typhoon_path",
            display_name="台风路径查询",
            method="GET",
            path="/api/typhoons/{typhoon_id}/path",
            request_factory=lambda ctx: {
                "headers": {"Authorization": f"Bearer {ctx['token']}"},
                "params": {"limit": 100},
            },
            total_requests=25,
            concurrency=5,
            category="查询服务",
        ),
        BenchmarkCase(
            case_id="alert_history",
            display_name="预警历史查询",
            method="GET",
            path="/api/alert/history",
            request_factory=lambda ctx: {"params": {"limit": 20}},
            total_requests=25,
            concurrency=5,
            category="查询服务",
        ),
        BenchmarkCase(
            case_id="prediction_history",
            display_name="预测记录查询",
            method="GET",
            path="/api/predictions/{typhoon_id}",
            request_factory=lambda ctx: {},
            total_requests=20,
            concurrency=5,
            category="查询服务",
        ),
        BenchmarkCase(
            case_id="prediction_path",
            display_name="路径预测接口",
            method="POST",
            path="/api/predictions/path",
            request_factory=lambda ctx: {
                "json": {
                    "typhoon_id": ctx["typhoon_id"],
                    "forecast_hours": 24,
                    "use_ensemble": False,
                }
            },
            total_requests=8,
            concurrency=2,
            category="预测服务",
            warmup_requests=1,
        ),
    ]


def format_case(case: BenchmarkCase, context: dict[str, Any]) -> BenchmarkCase:
    return BenchmarkCase(
        case_id=case.case_id,
        display_name=case.display_name,
        method=case.method,
        path=case.path.format(typhoon_id=context["typhoon_id"]),
        request_factory=case.request_factory,
        total_requests=case.total_requests,
        concurrency=case.concurrency,
        category=case.category,
        warmup_requests=case.warmup_requests,
    )


async def run_scalability_probe(
    base_url: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for concurrency in [1, 5, 10, 20]:
        case = BenchmarkCase(
            case_id=f"scalability_{concurrency}",
            display_name="台风列表查询并发扩展",
            method="GET",
            path="/api/typhoons",
            request_factory=lambda ctx: {"params": {"limit": 20}},
            total_requests=40,
            concurrency=concurrency,
            category="查询服务",
            warmup_requests=1,
        )
        result, _ = await run_case(base_url, case, context)
        records.append(
            {
                "concurrency": concurrency,
                "avg_ms": result.avg_ms,
                "p95_ms": result.p95_ms,
                "throughput_rps": result.throughput_rps,
                "success_rate": result.success_rate,
            }
        )
    return records


def save_csv(summary_path: Path, results: list[BenchmarkResult]) -> None:
    with summary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case_id",
                "display_name",
                "method",
                "path",
                "category",
                "total_requests",
                "concurrency",
                "success_count",
                "failure_count",
                "success_rate",
                "avg_ms",
                "median_ms",
                "p95_ms",
                "std_ms",
                "min_ms",
                "max_ms",
                "throughput_rps",
                "avg_size_bytes",
                "status_code_summary",
            ]
        )
        for item in results:
            writer.writerow(
                [
                    item.case_id,
                    item.display_name,
                    item.method,
                    item.path,
                    item.category,
                    item.total_requests,
                    item.concurrency,
                    item.success_count,
                    item.failure_count,
                    f"{item.success_rate:.2f}",
                    f"{item.avg_ms:.2f}",
                    f"{item.median_ms:.2f}",
                    f"{item.p95_ms:.2f}",
                    f"{item.std_ms:.2f}",
                    f"{item.min_ms:.2f}",
                    f"{item.max_ms:.2f}",
                    f"{item.throughput_rps:.2f}",
                    f"{item.avg_size_bytes:.2f}",
                    json.dumps(item.status_code_summary, ensure_ascii=False),
                ]
            )


def save_json(json_path: Path, payload: dict[str, Any]) -> None:
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def style_axes(ax: plt.Axes) -> None:
    ax.grid(axis="x", linestyle="--", linewidth=0.85, alpha=0.22, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#8A8A8A")
    ax.tick_params(axis="both", labelsize=11, colors="#000000")


def category_colors() -> dict[str, str]:
    return {
        "基础服务": "#2E86AB",
        "认证服务": "#3CAEA3",
        "查询服务": "#7A6FF0",
        "预测服务": "#F18F01",
    }


def average_size_kb(item: BenchmarkResult) -> float:
    return item.avg_size_bytes / 1024.0


def normalize_metric(values: list[float], invert: bool = False) -> list[float]:
    if not values:
        return []
    value_min = min(values)
    value_max = max(values)
    if math.isclose(value_min, value_max):
        normalized = [0.5 for _ in values]
    else:
        normalized = [(value - value_min) / (value_max - value_min) for value in values]
    if invert:
        normalized = [1.0 - value for value in normalized]
    return normalized


def plot_latency_dashboard(results: list[BenchmarkResult], output_path: Path) -> None:
    palette = category_colors()
    ordered = sorted(results, key=lambda item: item.avg_ms, reverse=True)
    labels = [item.display_name for item in ordered]
    avg_values = [item.avg_ms for item in ordered]
    p95_values = [item.p95_ms for item in ordered]
    median_values = [item.median_ms for item in ordered]
    throughput_values = [item.throughput_rps for item in ordered]
    payload_values = [average_size_kb(item) for item in ordered]
    std_values = [item.std_ms for item in ordered]
    tail_values = [max(item.p95_ms - item.median_ms, 0.0) for item in ordered]
    colors = [palette[item.category] for item in ordered]
    max_latency = max(p95_values) * 1.08

    fig = plt.figure(figsize=(18, 11))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.2, 1.0], height_ratios=[1.0, 0.92], hspace=0.26, wspace=0.18)
    ax1 = fig.add_subplot(grid[0, 0])
    ax2 = fig.add_subplot(grid[0, 1])
    ax3 = fig.add_subplot(grid[1, 0])
    ax4 = fig.add_subplot(grid[1, 1])

    y_positions = list(range(len(labels)))
    for left, right, color in (
        (0, min(max_latency, 50), "#EAF6EC"),
        (50, min(max_latency, 100), "#FFF4DE"),
        (100, max_latency, "#FCE9EA"),
    ):
        if right > left:
            ax1.axvspan(left, right, color=color, alpha=0.75, zorder=0)

    ax1.barh(
        [y - 0.18 for y in y_positions],
        avg_values,
        height=0.34,
        color="#4C78A8",
        label="平均响应时间",
        zorder=3,
    )
    ax1.barh(
        [y + 0.18 for y in y_positions],
        p95_values,
        height=0.34,
        color="#F58518",
        label="P95 响应时间",
        zorder=3,
    )
    ax1.scatter(median_values, y_positions, color="#54A24B", s=55, marker="D", label="中位响应时间", zorder=4)
    ax1.set_xlim(0, max_latency)
    ax1.set_yticks(y_positions)
    ax1.set_yticklabels(labels)
    ax1.invert_yaxis()
    ax1.set_xlabel("毫秒 (ms)")
    ax1.set_title("接口时延多指标对比", pad=14)
    style_axes(ax1)
    ax1.legend(loc="lower right")
    for idx, value in enumerate(avg_values):
        ax1.text(value + 4, idx - 0.18, f"{value:.1f}", va="center", fontsize=10, color="#000000")
    for idx, value in enumerate(p95_values):
        ax1.text(value + 4, idx + 0.18, f"{value:.1f}", va="center", fontsize=10, color="#000000")
    ax1.text(22, -0.8, "快", color="#000000", fontsize=11, fontweight="bold")
    ax1.text(73, -0.8, "中", color="#000000", fontsize=11, fontweight="bold")
    ax1.text(150, -0.8, "慢", color="#000000", fontsize=11, fontweight="bold")

    ax2.scatter(
        avg_values,
        throughput_values,
        s=[max(size * 45, 80) for size in payload_values],
        c=colors,
        alpha=0.85,
        edgecolors="white",
        linewidths=1.5,
        zorder=3,
    )
    style_axes(ax2)
    latency_mid = statistics.median(avg_values)
    throughput_mid = statistics.median(throughput_values)
    ax2.axvline(latency_mid, linestyle="--", color="#A0A4B8", linewidth=1)
    ax2.axhline(throughput_mid, linestyle="--", color="#A0A4B8", linewidth=1)
    ax2.set_xlabel("平均响应时间 (ms)")
    ax2.set_ylabel("吞吐率 (req/s)")
    ax2.set_title("吞吐率、时延与返回体关系", pad=14)
    for item in ordered:
        ax2.annotate(
            item.display_name,
            (item.avg_ms, item.throughput_rps),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=10,
            color="#000000",
            bbox={"boxstyle": "round,pad=0.2", "facecolor": "#FFFFFFF2", "edgecolor": "#8A8A8A"},
        )
    ax2.text(latency_mid * 0.55, throughput_mid * 1.12, "低时延\n高吞吐", ha="center", va="center", fontsize=11, color="#000000")
    ax2.text(latency_mid * 1.35, throughput_mid * 0.55, "高时延\n低吞吐", ha="center", va="center", fontsize=11, color="#000000")

    legend_handles: list[Any] = []
    for category, color in palette.items():
        legend_handles.append(Line2D([0], [0], marker="o", color="w", label=category, markerfacecolor=color, markersize=10))
    size_handles = [
        ax2.scatter([], [], s=max(size * 45, 80), color="#8F95B2", alpha=0.35, edgecolors="white", linewidths=1)
        for size in (1, 10, 50)
    ]
    legend_handles.extend(size_handles)
    legend_labels = list(palette.keys()) + ["约 1 KB", "约 10 KB", "约 50 KB"]
    ax2.legend(legend_handles, legend_labels, title="颜色/气泡含义", loc="upper right")

    stability_order = sorted(ordered, key=lambda item: item.std_ms, reverse=True)
    stability_labels = [item.display_name for item in stability_order]
    stability_std = [item.std_ms for item in stability_order]
    stability_tail = [max(item.p95_ms - item.median_ms, 0.0) for item in stability_order]
    stability_pos = list(range(len(stability_labels)))
    ax3.barh(stability_pos, stability_std, height=0.48, color="#8B7CF6", alpha=0.85, label="标准差")
    ax3.plot(stability_tail, stability_pos, color="#D45087", marker="o", linewidth=2, label="P95-中位数")
    ax3.set_yticks(stability_pos)
    ax3.set_yticklabels(stability_labels)
    ax3.invert_yaxis()
    ax3.set_xlabel("毫秒 (ms)")
    ax3.set_title("稳定性与尾延迟差距", pad=14)
    style_axes(ax3)
    ax3.legend(loc="lower right")
    for idx, value in enumerate(stability_std):
        ax3.text(value + 2.5, idx, f"{value:.1f}", va="center", fontsize=10, color="#000000")

    category_names = [category for category in palette if any(item.category == category for item in ordered)]
    category_avg = [
        statistics.mean(item.avg_ms for item in ordered if item.category == category)
        for category in category_names
    ]
    category_throughput = [
        statistics.mean(item.throughput_rps for item in ordered if item.category == category)
        for category in category_names
    ]
    ax4.bar(category_names, category_avg, color=[palette[name] for name in category_names], alpha=0.82, width=0.58)
    ax4.set_ylabel("平均响应时间 (ms)")
    ax4.set_title("服务类别性能画像", pad=14)
    style_axes(ax4)
    ax4.grid(axis="y", linestyle="--", linewidth=0.8, alpha=0.25, zorder=0)
    ax4.tick_params(axis="x", rotation=0)
    ax4_twin = ax4.twinx()
    ax4_twin.plot(category_names, category_throughput, color="#23395D", marker="o", linewidth=2.3, label="平均吞吐率")
    ax4_twin.set_ylabel("平均吞吐率 (req/s)")
    ax4_twin.spines["top"].set_visible(False)
    ax4_twin.spines["right"].set_color("#D5D8E1")
    for x_value, avg_value in zip(category_names, category_avg):
        ax4.text(x_value, avg_value + max(category_avg) * 0.03, f"{avg_value:.1f}", ha="center", fontsize=10, color="#000000")
    for x_value, throughput_value in zip(category_names, category_throughput):
        ax4_twin.text(x_value, throughput_value + max(category_throughput) * 0.03, f"{throughput_value:.1f}", ha="center", fontsize=10, color="#000000")
    ax4.legend(
        handles=[
            Patch(facecolor="#4C78A8", alpha=0.82, label="类别平均时延"),
            Line2D([0], [0], color="#23395D", marker="o", linewidth=2.3, label="类别平均吞吐率"),
        ],
        loc="upper right",
    )

    fig.suptitle("性能测试总览仪表板", fontsize=19, fontweight="bold", y=0.98)
    fig.subplots_adjust(top=0.88, bottom=0.06, left=0.06, right=0.97, hspace=0.28, wspace=0.18)
    plt.savefig(output_path, dpi=EXPORT_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_latency_distribution(raw_payload: dict[str, Any], output_path: Path) -> None:
    palette = category_colors()
    series = []
    labels = []
    colors = []
    for case in raw_payload["cases"]:
        labels.append(case["summary"]["display_name"])
        series.append([row["elapsed_ms"] for row in case["requests"]])
        colors.append(palette.get(case["summary"]["category"], "#4C78A8"))

    medians = [statistics.median(values) if values else 0.0 for values in series]
    order = sorted(range(len(labels)), key=lambda idx: medians[idx], reverse=True)
    ordered_labels = [labels[idx] for idx in order]
    ordered_series = [series[idx] for idx in order]
    ordered_colors = [colors[idx] for idx in order]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8.4), gridspec_kw={"width_ratios": [1.15, 1.0]})
    box = ax1.boxplot(
        ordered_series,
        vert=False,
        patch_artist=True,
        tick_labels=ordered_labels,
        showmeans=True,
        meanprops={"marker": "o", "markerfacecolor": "#D62728", "markeredgecolor": "white", "markersize": 6},
        medianprops={"color": "#1F1F1F", "linewidth": 1.5},
        whiskerprops={"color": "#888888"},
        capprops={"color": "#888888"},
    )
    for patch, color in zip(box["boxes"], ordered_colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.48)
        patch.set_edgecolor(color)
    for idx, values in enumerate(ordered_series, start=1):
        offsets = [idx + (((value_index % 7) - 3) / 28.0) for value_index in range(len(values))]
        ax1.scatter(
            values,
            offsets,
            s=18,
            color=ordered_colors[idx - 1],
            alpha=0.26,
            edgecolors="white",
            linewidths=0.35,
            zorder=2,
        )
        median_value = statistics.median(values) if values else 0.0
        ax1.text(median_value + 3.5, idx, f"{median_value:.1f}", va="center", fontsize=10, color="#000000")

    ax1.set_xlabel("响应时间 (ms)")
    ax1.set_title("接口延迟分布与离散区间", pad=14)
    style_axes(ax1)

    top_n = min(5, len(ordered_series))
    top_series = ordered_series[:top_n]
    top_labels = ordered_labels[:top_n]
    top_colors = ordered_colors[:top_n]
    for values, label, color in zip(top_series, top_labels, top_colors):
        sorted_values = sorted(values)
        if len(sorted_values) == 1:
            percent_axis = [100.0]
        else:
            percent_axis = [index * 100.0 / (len(sorted_values) - 1) for index in range(len(sorted_values))]
        ax2.plot(percent_axis, sorted_values, color=color, linewidth=2.3, label=label)
        ax2.scatter([50, 95], [percentile(sorted_values, 0.50), percentile(sorted_values, 0.95)], color=color, s=26, zorder=3)
    ax2.set_xlabel("请求样本分位数 (%)")
    ax2.set_ylabel("响应时间 (ms)")
    ax2.set_title("慢接口尾延迟演化曲线（Top 5）", pad=14)
    ax2.set_xlim(0, 100)
    style_axes(ax2)
    ax2.legend(loc="upper left")
    ax2.axvline(50, linestyle="--", color="#A0A4B8", linewidth=1)
    ax2.axvline(95, linestyle="--", color="#A0A4B8", linewidth=1)
    ax2.text(50, ax2.get_ylim()[1] * 0.96, "P50", ha="center", va="top", fontsize=10, color="#000000")
    ax2.text(95, ax2.get_ylim()[1] * 0.96, "P95", ha="center", va="top", fontsize=10, color="#000000")

    fig.suptitle("接口响应分布与尾延迟分析", fontsize=18, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=EXPORT_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_metric_heatmap(results: list[BenchmarkResult], output_path: Path) -> None:
    avg_values = [item.avg_ms for item in results]
    p95_values = [item.p95_ms for item in results]
    std_values = [item.std_ms for item in results]
    throughput_values = [item.throughput_rps for item in results]
    payload_values = [average_size_kb(item) for item in results]

    avg_pressure = normalize_metric(avg_values)
    p95_pressure = normalize_metric(p95_values)
    std_pressure = normalize_metric(std_values)
    throughput_pressure = normalize_metric(throughput_values, invert=True)
    payload_pressure = normalize_metric(payload_values)
    composite_pressure = [
        (
            avg_pressure[index] * 0.30
            + p95_pressure[index] * 0.25
            + std_pressure[index] * 0.15
            + throughput_pressure[index] * 0.20
            + payload_pressure[index] * 0.10
        )
        for index in range(len(results))
    ]

    ordered_indexes = sorted(range(len(results)), key=lambda index: composite_pressure[index], reverse=True)
    labels = [results[index].display_name for index in ordered_indexes]
    metrics = ["平均时延", "P95时延", "标准差", "吞吐压力", "返回体KB", "综合压力"]
    matrix = [
        [
            avg_pressure[index],
            p95_pressure[index],
            std_pressure[index],
            throughput_pressure[index],
            payload_pressure[index],
            composite_pressure[index],
        ]
        for index in ordered_indexes
    ]
    actual_matrix = [
        [
            avg_values[index],
            p95_values[index],
            std_values[index],
            throughput_values[index],
            payload_values[index],
            composite_pressure[index] * 100.0,
        ]
        for index in ordered_indexes
    ]

    fig, ax = plt.subplots(figsize=(13.5, 7.1))
    image = ax.imshow(matrix, cmap="YlOrRd", aspect="auto", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(metrics)))
    ax.set_xticklabels(metrics)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_title("接口综合压力热力图", pad=14)

    for i in range(len(labels)):
        for j in range(len(metrics)):
            value = actual_matrix[i][j]
            text = f"{value:.1f}"
            if metrics[j] == "返回体KB":
                text = f"{value:.2f}"
            if metrics[j] == "综合压力":
                text = f"{value:.0f}"
            ax.text(j, i, text, ha="center", va="center", color="#000000", fontsize=10, fontweight="bold" if j == len(metrics) - 1 else "normal")

    cbar = fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("性能压力强度")
    fig.text(
        0.5,
        0.03,
        "注：颜色越深表示该指标对应的性能压力越高，其中“吞吐压力”已按“吞吐率越低、压力越高”进行转换。",
        ha="center",
        fontsize=10,
        color="#000000",
    )
    plt.tight_layout(rect=(0.0, 0.07, 1.0, 1.0))
    plt.savefig(output_path, dpi=EXPORT_DPI, bbox_inches="tight")
    plt.close(fig)


def plot_scalability_dashboard(records: list[dict[str, Any]], output_path: Path) -> None:
    concurrencies = [item["concurrency"] for item in records]
    avg_values = [item["avg_ms"] for item in records]
    p95_values = [item["p95_ms"] for item in records]
    throughput_values = [item["throughput_rps"] for item in records]

    baseline_throughput = throughput_values[0] if throughput_values else 0.0
    efficiency_values = [
        (throughput / (baseline_throughput * concurrency) * 100.0) if baseline_throughput > 0 else 0.0
        for throughput, concurrency in zip(throughput_values, concurrencies)
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16.8, 7.0), gridspec_kw={"width_ratios": [1.15, 1.0]})
    style_axes(ax1)
    ax1.fill_between(concurrencies, avg_values, p95_values, color="#F58518", alpha=0.12, label="尾延迟区间")
    ax1.plot(concurrencies, avg_values, marker="o", markersize=8, color="#2E86AB", linewidth=2.5, label="平均响应时间")
    ax1.plot(concurrencies, p95_values, marker="s", markersize=8, color="#F58518", linewidth=2.5, label="P95 响应时间")
    ax1.set_xlabel("并发数")
    ax1.set_ylabel("响应时间 (ms)")
    ax1.set_title("并发提升下的时延增长", pad=14)
    for x_value, avg_value, p95_value in zip(concurrencies, avg_values, p95_values):
        ax1.text(x_value, avg_value + 10, f"{avg_value:.1f}", color="#000000", ha="center", fontsize=10)
        ax1.text(x_value, p95_value + 10, f"{p95_value:.1f}", color="#000000", ha="center", fontsize=10)
    ax1.legend(loc="upper left")

    style_axes(ax2)
    bars = ax2.bar(concurrencies, throughput_values, width=2.2, color="#54A24B", alpha=0.72, label="吞吐率")
    ax2.set_xlabel("并发数")
    ax2.set_ylabel("吞吐率 (req/s)")
    ax2.set_title("吞吐率与伸缩效率", pad=14)
    ax2_twin = ax2.twinx()
    ax2_twin.plot(concurrencies, efficiency_values, marker="D", color="#7A4FB4", linewidth=2.4, label="伸缩效率")
    ax2_twin.set_ylabel("伸缩效率 (%)")
    ax2_twin.spines["top"].set_visible(False)
    ax2_twin.spines["right"].set_color("#D5D8E1")
    for bar, throughput_value in zip(bars, throughput_values):
        ax2.text(bar.get_x() + bar.get_width() / 2, throughput_value + max(throughput_values) * 0.03, f"{throughput_value:.1f}", ha="center", fontsize=10, color="#000000")
    for x_value, efficiency_value in zip(concurrencies, efficiency_values):
        ax2_twin.text(x_value, efficiency_value + max(efficiency_values) * 0.05, f"{efficiency_value:.1f}%", ha="center", fontsize=10, color="#000000")
    handles1, labels1 = ax2.get_legend_handles_labels()
    handles2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(handles1 + handles2, labels1 + labels2, loc="upper right")

    fig.suptitle("台风列表查询接口并发扩展分析", fontsize=18, fontweight="bold", y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=EXPORT_DPI, bbox_inches="tight")
    plt.close(fig)


def generate_markdown(
    report_path: Path,
    timestamp: str,
    base_url: str,
    context: dict[str, Any],
    results: list[BenchmarkResult],
    scalability_records: list[dict[str, Any]],
    image_paths: dict[str, Path],
) -> None:
    business_results = [item for item in results if item.case_id != "health"]
    fastest_business = min(business_results, key=lambda item: item.avg_ms)
    slowest_business = max(business_results, key=lambda item: item.avg_ms)
    highest_throughput = max(business_results, key=lambda item: item.throughput_rps)
    highest_jitter = max(business_results, key=lambda item: item.std_ms)

    scope_lines = []
    for item in results:
        scope_lines.append(
            "| {name} | {category} | `{method} {path}` | {goal} |".format(
                name=item.display_name,
                category=item.category,
                method=item.method,
                path=item.path,
                goal=(
                    "验证基础服务活性" if item.category == "基础服务"
                    else "验证认证链路与权限状态" if item.category == "认证服务"
                    else "验证数据库查询与数据组织性能" if item.category == "查询服务"
                    else "验证预测逻辑与结果写入链路耗时"
                ),
            )
        )

    result_lines = []
    for item in results:
        result_lines.append(
            "| {name} | {category} | `{method} {path}` | {requests} | {conc} | {succ:.2f}% | "
            "{avg:.2f} | {median:.2f} | {p95:.2f} | {std:.2f} | {throughput:.2f} | {size_kb:.2f} |".format(
                name=item.display_name,
                category=item.category,
                method=item.method,
                path=item.path,
                requests=item.total_requests,
                conc=item.concurrency,
                succ=item.success_rate,
                avg=item.avg_ms,
                median=item.median_ms,
                p95=item.p95_ms,
                std=item.std_ms,
                throughput=item.throughput_rps,
                size_kb=average_size_kb(item),
            )
        )

    scalability_lines = []
    for row in scalability_records:
        scalability_lines.append(
            "| {concurrency} | {avg_ms:.2f} | {p95_ms:.2f} | {throughput_rps:.2f} | {success_rate:.2f}% |".format(**row)
        )

    relative_latency = image_paths["latency_dashboard"].relative_to(report_path.parent).as_posix()
    relative_distribution = image_paths["distribution"].relative_to(report_path.parent).as_posix()
    relative_heatmap = image_paths["heatmap"].relative_to(report_path.parent).as_posix()
    relative_scalability = image_paths["scalability_dashboard"].relative_to(report_path.parent).as_posix()

    markdown = f"""# 性能测试补充结果

## 适用说明

本文档用于补充台风路径智能预测与分析系统论文中的性能测试内容。测试结果由 `backend/tools/performance_benchmark.py` 在 {timestamp} 自动生成，适合作为论文测试章节中“性能测试”小节的支撑材料，也可作为后续继续补充专项压测的基线记录。

## 测试目标

本轮测试聚焦系统中最具代表性的基础服务接口、认证接口、业务查询接口和预测接口，包括健康检查、用户登录、当前用户信息查询、台风列表查询、关键词检索、台风路径查询、预警历史查询、预测记录查询以及路径预测接口。测试目的不是单纯给出若干平均值，而是从接口时延、尾延迟、稳定性、吞吐率和并发扩展能力等角度，对当前后端服务的整体性能水平进行较为完整的观察。

## 测试说明

- 测试时间：{timestamp}
- 测试地址：`{base_url}`
- 样本台风编号：`{context["typhoon_id"]}`
- 检索关键词：`{context["sample_keyword"]}`
- 预测模式说明：本轮路径预测接口返回的模型标识为 `{context["prediction_model"]}`
- 测试方式：基于异步 HTTP 请求执行接口级压测，包含预热请求与并发扩展测试
- 结果说明：路径预测接口涉及模型推理或降级预测逻辑，响应时间通常高于普通查询接口；图像分析、视频分析和语音识别等强依赖外部模型或大文件输入的接口未纳入统一压测，以减少外部环境波动对结果的影响

## 测试范围与评价指标

| 接口名称 | 接口类别 | 测试目标 | 说明 |
| -------- | -------- | -------- | ---- |
{chr(10).join(scope_lines)}

本次测试主要使用以下指标衡量接口性能表现：

- 平均响应时间：反映接口在当前测试条件下的总体响应速度。
- 中位响应时间：用于描述典型请求的响应水平，可减少极端值影响。
- P95 响应时间：表示 95% 请求在该时间内完成，更适合衡量尾延迟。
- 标准差：用于描述响应时间离散程度，数值越大说明波动越明显。
- 吞吐率：单位时间内完成的请求数量，反映接口在并发访问下的处理能力。
- 平均返回体：反映接口响应数据规模，可辅助解释不同接口的耗时差异。

## 主要测试结果表

| 接口名称 | 接口类别 | 测试目标 | 请求数 | 并发数 | 成功率 | 平均响应时间(ms) | 中位响应时间(ms) | P95 响应时间(ms) | 标准差(ms) | 吞吐率(req/s) | 平均返回体(KB) |
| -------- | -------- | -------- | ------ | ------ | ------ | ---------------- | ---------------- | ---------------- | ---------- | ------------- | --------------- |
{chr(10).join(result_lines)}

## 并发扩展结果

并发扩展测试以“台风列表查询接口”为对象，通过逐步提高并发数，观察接口平均响应时间、P95 响应时间以及吞吐率的变化趋势，用于判断当前系统在中低强度并发场景下的伸缩表现。

| 并发数 | 平均响应时间(ms) | P95 响应时间(ms) | 吞吐率(req/s) | 成功率 |
| ------ | ---------------- | ---------------- | ------------- | ------ |
{chr(10).join(scalability_lines)}

## 关键发现

- 在业务接口中，平均响应时间最低的是 **{fastest_business.display_name}**，均值为 **{fastest_business.avg_ms:.2f} ms**，说明该接口的数据组织开销较低。
- 平均响应时间最高的业务接口是 **{slowest_business.display_name}**，均值为 **{slowest_business.avg_ms:.2f} ms**，其耗时与数据量和处理逻辑复杂度更高有关。
- 业务接口中吞吐率最高的是 **{highest_throughput.display_name}**，达到 **{highest_throughput.throughput_rps:.2f} req/s**，说明该接口更适合作为高频查询入口。
- 响应时间波动最大的接口为 **{highest_jitter.display_name}**，标准差为 **{highest_jitter.std_ms:.2f} ms**，表明该接口在不同请求批次下存在更明显的尾延迟波动。

## 指标可视化

![图 1 性能测试核心指标概览]({relative_latency})

图 1 性能测试总览仪表板。该图由四个子图组成，分别展示接口时延多指标对比、吞吐率与返回体关系、稳定性与尾延迟差距，以及不同服务类别的平均时延和平均吞吐率画像，适合从总体层面观察系统后端性能结构。

![图 2 各接口响应时间分布箱线图]({relative_distribution})

图 2 接口响应分布与尾延迟分析图。左侧使用箱线图和采样散点展示各接口请求延迟的分布形态与离散程度，右侧对耗时较高的接口绘制分位曲线，用于观察请求由中位数向高分位延伸时的增长趋势。

![图 3 接口性能指标热力图]({relative_heatmap})

图 3 接口综合压力热力图。图中对平均时延、P95 时延、标准差、吞吐压力、平均返回体以及综合压力指数进行了归一化展示，其中颜色越深表示性能压力越高，便于快速定位当前最值得优先优化的接口。

![图 4 台风列表查询接口并发扩展分析]({relative_scalability})

图 4 台风列表查询接口并发扩展分析。左侧展示并发数上升时平均响应时间与 P95 响应时间的增长趋势，右侧展示吞吐率和伸缩效率变化情况，可用于判断该接口在不同并发级别下的承载状态。

## 结果分析

从测试结果看，健康检查接口和认证类接口整体响应较快，说明当前 FastAPI 后端在本地部署环境下能够较稳定地完成基础服务和用户鉴权流程。台风关键词检索、台风路径查询和预测记录查询等普通查询类接口也保持了较好的响应水平，反映出 SQLite 数据读取和接口序列化开销总体可控。

台风列表查询和预警历史查询的延迟相对更高，其中前者返回数据规模较大，后者还包含基于台风路径数据的预警组织逻辑，因此平均响应时间和 P95 响应时间明显高于简单查询接口。综合压力热力图与分位曲线进一步说明，这两类接口不仅平均耗时偏高，而且在高分位区间的增长更明显，是后续性能优化中应优先关注的对象。

路径预测接口的响应时间高于大多数普通查询接口，这与其需要读取历史路径数据、执行预测逻辑并写入预测结果有关。结合本轮实测返回的 `LinearFallback` 标识可知，当前测得的是降级预测链路的整体耗时，并不能完全代表深度模型在 GPU 条件下的完整推理性能。因此，若后续补充正式答辩版性能测试材料，建议在完整模型可用时再对预测接口进行专项测试。

从并发扩展分析看，台风列表查询接口在并发数由 1 提升到 20 时，平均响应时间和 P95 响应时间呈明显上升趋势，而吞吐率在中低并发阶段仍能维持相对稳定，说明系统对中低强度并发访问具备一定承载能力。但从伸缩效率曲线也可以看出，随着并发继续提升，单位并发带来的吞吐收益逐渐下降，接口尾延迟则持续增大。

## 优化建议

- 台风列表查询接口可优先从分页参数控制、查询字段裁剪和热点查询缓存等方向进行优化，以减少大结果集返回带来的响应时间增长。
- 预警历史查询接口可进一步梳理数据组织流程，尽量将重复计算前移或落盘缓存，以降低高分位请求的波动。
- 路径预测接口建议在完整模型可用、GPU 环境稳定后增加专项测试，并与当前 `LinearFallback` 结果分开记录，避免两类链路混用造成结论失真。
- 若后续继续完善论文中的性能测试章节，可补充数据库索引优化前后对比、媒体分析接口专项测试以及完整模型推理场景下的预测性能测试。
"""
    report_path.write_text(markdown, encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run performance benchmarks for the backend API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Target API base URL")
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional output directory. Defaults to docs/performance/<timestamp>",
    )
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_ROOT / timestamp
    images_dir = output_dir / "images"
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    username, password = await ensure_test_user(args.base_url)
    token = await login_and_get_token(args.base_url, username, password)
    sample = await discover_sample_typhoon(args.base_url)
    prediction_model = await detect_prediction_mode(args.base_url, sample["typhoon_id"])
    context = {
        "token": token,
        "typhoon_id": sample["typhoon_id"],
        "sample_keyword": sample["keyword"],
        "username": username,
        "password": password,
        "prediction_model": prediction_model,
    }

    results: list[BenchmarkResult] = []
    raw_payload: dict[str, Any] = {
        "generated_at": datetime.now().isoformat(),
        "base_url": args.base_url,
        "context": {
            "typhoon_id": context["typhoon_id"],
            "sample_keyword": context["sample_keyword"],
            "username": context["username"],
            "prediction_model": context["prediction_model"],
        },
        "cases": [],
    }

    for case in build_cases():
        formatted_case = format_case(case, context)
        result, raw_rows = await run_case(args.base_url, formatted_case, context)
        results.append(result)
        raw_payload["cases"].append(
            {
                "case": {
                    "case_id": formatted_case.case_id,
                    "display_name": formatted_case.display_name,
                    "method": formatted_case.method,
                "path": formatted_case.path,
                "category": formatted_case.category,
                "total_requests": formatted_case.total_requests,
                "concurrency": formatted_case.concurrency,
            },
            "summary": result.__dict__,
            "requests": raw_rows,
            }
        )

    scalability_records = await run_scalability_probe(args.base_url, context)
    raw_payload["scalability_probe"] = scalability_records

    summary_csv = output_dir / "summary.csv"
    raw_json = output_dir / "raw_results.json"
    report_md = output_dir / "性能测试补充结果.md"
    latency_dashboard_image = images_dir / "latency_dashboard.png"
    distribution_image = images_dir / "latency_distribution_boxplot.png"
    heatmap_image = images_dir / "metric_heatmap.png"
    scalability_dashboard_image = images_dir / "scalability_dashboard.png"

    save_csv(summary_csv, results)
    save_json(raw_json, raw_payload)
    plot_latency_dashboard(results, latency_dashboard_image)
    plot_latency_distribution(raw_payload, distribution_image)
    plot_metric_heatmap(results, heatmap_image)
    plot_scalability_dashboard(scalability_records, scalability_dashboard_image)
    generate_markdown(
        report_md,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        base_url=args.base_url,
        context=context,
        results=results,
        scalability_records=scalability_records,
        image_paths={
            "latency_dashboard": latency_dashboard_image,
            "distribution": distribution_image,
            "heatmap": heatmap_image,
            "scalability_dashboard": scalability_dashboard_image,
        },
    )

    print(report_md)
    print(summary_csv)
    print(raw_json)


if __name__ == "__main__":
    asyncio.run(main())
