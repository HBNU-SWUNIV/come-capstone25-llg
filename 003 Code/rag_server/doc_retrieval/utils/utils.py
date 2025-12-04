import datetime
import numpy as np
import time

def format_time(elapsed):
    elapsed_rounded = int(round((elapsed)))  # Round to the nearest second.
    return str(datetime.timedelta(seconds=elapsed_rounded))  # Format as hh:mm:ss


def _is_hit(ridx, answer):
    """
    ridx: retrieved index (int or str)
    answer: 단일 정답 또는 [정답1, 정답2, ...] 형태
    """
    if isinstance(answer, (list, set, tuple, np.ndarray)):
        return ridx in answer
    return ridx == answer


def _to_answer_set(answer):
    """answer를 집합(set) 형태의 정답 집합으로 변환"""
    if isinstance(answer, (list, set, tuple, np.ndarray)):
        return set(answer)
    return {answer}


def _mrr_ap_for_query(ranked_ids, answer, max_k=100):
    """
    한 쿼리에 대해 MRR, AP 계산
    ranked_ids: 검색 결과 doc id 리스트
    answer: 단일/복수 정답
    """
    ans_set = _to_answer_set(answer)
    if not ans_set:
        return 0.0, 0.0

    mrr = 0.0
    num_rel = 0
    sum_prec = 0.0

    for rank, ridx in enumerate(ranked_ids[:max_k]):
        if ridx in ans_set:
            num_rel += 1
            # MRR: 첫 번째로 맞춘 위치
            if mrr == 0.0:
                mrr = 1.0 / (rank + 1)
            # AP: precision@rank 누적
            sum_prec += num_rel / (rank + 1)

    if num_rel == 0:
        ap = 0.0
    else:
        # 정답 개수 기준 평균
        ap = sum_prec / len(ans_set)

    return mrr, ap


def get_topk_accuracy(faiss_index, answer_idx, positive_idx):
    # top-k hit 수
    top1_correct = 0
    top2_correct = 0
    top3_correct = 0
    top5_correct = 0
    top10_correct = 0
    top20_correct = 0
    top30_correct = 0
    top50_correct = 0
    top100_correct = 0

    # 추가 IR 지표용
    mrr_sum = 0.0     # MRR@100
    map_sum = 0.0     # MAP@100

    start_time = time.perf_counter()

    for idx, answer in enumerate(answer_idx):
        retrieved_idx = faiss_index[idx]
        # faiss에서 나온 인덱스를 text_index(or positive_idx) 기준 인덱스로 매핑
        retrieved_idx = [positive_idx[jdx] for jdx in retrieved_idx]

        # ----- top-k hit -----
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:1]):
            top1_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:2]):
            top2_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:3]):
            top3_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:5]):
            top5_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:10]):
            top10_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:20]):
            top20_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:30]):
            top30_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:50]):
            top50_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:100]):
            top100_correct += 1

        mrr_i, ap_i = _mrr_ap_for_query(retrieved_idx, answer, max_k=100)
        mrr_sum += mrr_i
        map_sum += ap_i

    end_time = time.perf_counter()
    total = len(answer_idx)

    return {
        'top1_accuracy':  top1_correct  / total,
        'top2_accuracy':  top2_correct  / total,
        'top3_accuracy':  top3_correct  / total,
        'top5_accuracy':  top5_correct  / total,
        'top10_accuracy': top10_correct / total,
        'top20_accuracy': top20_correct / total,
        'top30_accuracy': top30_correct / total,
        'top50_accuracy': top50_correct / total,
        'top100_accuracy': top100_correct / total,
        'mrr@100': mrr_sum / total,
        'map@100': map_sum / total,
        'elapsed': format_time(end_time - start_time),
    }


def get_topk_accuracy_cross(predictions, answer_idx):
    # predictions: (num_queries, k) 형태의 doc id 리스트/배열
    top1_correct = 0
    top2_correct = 0
    top3_correct = 0
    top5_correct = 0
    top10_correct = 0
    top20_correct = 0
    top30_correct = 0
    top50_correct = 0
    top100_correct = 0

    mrr_sum = 0.0
    map_sum = 0.0

    for idx, answer in enumerate(answer_idx):
        retrieved_idx = predictions[idx]

        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:1]):
            top1_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:2]):
            top2_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:3]):
            top3_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:5]):
            top5_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:10]):
            top10_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:20]):
            top20_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:30]):
            top30_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:50]):
            top50_correct += 1
        if any(_is_hit(ridx, answer) for ridx in retrieved_idx[:100]):
            top100_correct += 1

        mrr_i, ap_i = _mrr_ap_for_query(retrieved_idx, answer, max_k=100)
        mrr_sum += mrr_i
        map_sum += ap_i

    total = len(answer_idx)

    return {
        'top1_accuracy':  top1_correct  / total,
        'top2_accuracy':  top2_correct  / total,
        'top3_accuracy':  top3_correct  / total,
        'top5_accuracy':  top5_correct  / total,
        'top10_accuracy': top10_correct / total,
        'top20_accuracy': top20_correct / total,
        'top30_accuracy': top30_correct / total,
        'top50_accuracy': top50_correct / total,
        'top100_accuracy': top100_correct / total,
        'mrr@100': mrr_sum / total,
        'map@100': map_sum / total,
    }
