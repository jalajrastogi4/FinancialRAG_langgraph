from graph.run import run_graph


def main():
    # query = "What is a 10-K report?"
    # run_graph(
    #     query=query,
    #     thread_id="thread_002",
    #     user_id="user_212",
    # )
    query = "Do a detailed analysis of Amazon's financial performance in 2023 and 2024"
    run_graph(
        query=query,
        thread_id="thread_001",
        user_id="user_210",
    )



if __name__ == "__main__":
    main()