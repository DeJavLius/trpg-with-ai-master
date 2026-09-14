from rag_with_trpg.config import load_config
from rag_with_trpg.diagnose.config import DiagnoseConfig
from rag_with_trpg.diagnose.diagnos import diagnose
from rag_with_trpg.diagnose.model_compare import compare


def main() -> None:
    print("[0] diagnose: config environment load")
    load_config()
    config = DiagnoseConfig.from_config()

    if config.do_diagnose:
        diagnose(config)

    if config.do_compare and config.do_model_compare:
        compare(config)


if __name__ == "__main__":
    main()
