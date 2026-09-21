from trpg_with_ai_master.config import load_config
from trpg_with_ai_master.crawl.config import CrawlConfig
from trpg_with_ai_master.crawl.convert import converter
from trpg_with_ai_master.crawl.crawl import crawler
from trpg_with_ai_master.crawl.index_mapped import (
    exclude_file_check,
    mapper,
    show_markdown_heading,
)


def main() -> None:
    print("[0] crawl: config environment load")
    load_config()
    config = CrawlConfig.from_config()
    init_files = list(config.raw_path.rglob("*.html"))

    print("[1] crawl: start raw file check and crawling")
    crawler(config, init_files)

    print("[2] crawl: start convert raw html into markdown")
    raw_files = list(config.raw_path.rglob("*.html"))
    check_md_files = list(config.md_path.rglob("*.md"))
    execute_exclude = converter(config, raw_files, check_md_files)

    print("[3] crawl: start markdown file heading check")
    converted_md_files = list(config.md_path.rglob("*.md"))

    print("[4] crawl: start making meta data with markdown & html")
    mapper(config, raw_files, converted_md_files)

    print("[5] result: file exclude checking")
    prev_exclude_count, exclude_files = exclude_file_check(config)

    if config.do_create and (
        (len(execute_exclude) != prev_exclude_count)
        or file_check(execute_exclude, exclude_files)
    ):
        raise RuntimeError(
            f"인덱스 제외: {len(execute_exclude)}건 (기대 {prev_exclude_count}건). "
            f"제외 파일 목록: {"".join([f"{t}.md " for t in execute_exclude])}"
            f"extract issue tracking recommended"
        )

    show_markdown_heading(config)
    print(f"변환 제외 파일: {", ".join([f"{e}" for e in exclude_files])}")


def file_check(a_list: list[str], b_list: list[str]) -> bool:
    return sorted(a_list) != sorted(b_list)


if __name__ == "__main__":
    main()
