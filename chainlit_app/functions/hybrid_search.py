from llama_index.core.vector_stores import VectorStoreQueryResult


def relative_score_fusion(
    dense_result: VectorStoreQueryResult,
    sparse_result: VectorStoreQueryResult,
    alpha: float = 0.5,  # passed in from the query engine
    top_k: int = 2,  # passed in from the query engine i.e. similarity_top_k
) -> VectorStoreQueryResult:
    """
    Fuse dense and sparse results using relative score fusion.
    """
    # sanity check
    assert dense_result.nodes is not None
    assert dense_result.similarities is not None
    assert sparse_result.nodes is not None
    assert sparse_result.similarities is not None

    # deconstruct results
    sparse_result_tuples = list(
        zip(sparse_result.similarities, sparse_result.nodes)
    )
    sparse_result_tuples.sort(key=lambda x: x[0], reverse=True)

    dense_result_tuples = list(
        zip(dense_result.similarities, dense_result.nodes)
    )
    dense_result_tuples.sort(key=lambda x: x[0], reverse=True)

    # track nodes in both results
    all_nodes_dict = {x.node_id: x for x in dense_result.nodes}
    for node in sparse_result.nodes:
        if node.node_id not in all_nodes_dict:
            all_nodes_dict[node.node_id] = node

    # normalize sparse similarities from 0 to 1
    sparse_similarities = [x[0] for x in sparse_result_tuples]
    max_sparse_sim = max(sparse_similarities)
    min_sparse_sim = min(sparse_similarities)
    sparse_similarities = [
        (x - min_sparse_sim) / (max_sparse_sim - min_sparse_sim)
        for x in sparse_similarities
    ]
    sparse_per_node = {
        sparse_result_tuples[i][1].node_id: x
        for i, x in enumerate(sparse_similarities)
    }

    # normalize dense similarities from 0 to 1
    dense_similarities = [x[0] for x in dense_result_tuples]
    max_dense_sim = max(dense_similarities)
    min_dense_sim = min(dense_similarities)
    dense_similarities = [
        (x - min_dense_sim) / (max_dense_sim - min_dense_sim)
        for x in dense_similarities
    ]
    dense_per_node = {
        dense_result_tuples[i][1].node_id: x
        for i, x in enumerate(dense_similarities)
    }

    # fuse the scores
    fused_similarities = []
    for node_id in all_nodes_dict:
        sparse_sim = sparse_per_node.get(node_id, 0)
        dense_sim = dense_per_node.get(node_id, 0)
        fused_sim = alpha * (sparse_sim + dense_sim)
        fused_similarities.append((fused_sim, all_nodes_dict[node_id]))

    fused_similarities.sort(key=lambda x: x[0], reverse=True)
    fused_similarities = fused_similarities[:top_k]

    # create final response object
    return VectorStoreQueryResult(
        nodes=[x[1] for x in fused_similarities],
        similarities=[x[0] for x in fused_similarities],
        ids=[x[1].node_id for x in fused_similarities],
    )