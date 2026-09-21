from trpg_with_ai_master.config import load_config
from trpg_with_ai_master.diagnose.config import DiagnoseConfig
from trpg_with_ai_master.diagnose.diagnos import diagnose
from trpg_with_ai_master.diagnose.model_compare import compare


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
