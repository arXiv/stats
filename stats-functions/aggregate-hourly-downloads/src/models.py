from typing import Set, Literal
from datetime import datetime

from arxiv.taxonomy.category import Category
from arxiv.taxonomy.definitions import CATEGORIES

DOWNLOAD_TYPE = Literal["pdf", "html", "src"]

class PaperCategories:
    paper_id: str
    primary: Category
    crosses: Set[Category]

    def __init__(self, id: str):
        self.paper_id = id
        self.primary = None
        self.crosses = set()

    def add_primary(self, cat: str):
        if self.primary != None:  # this function should only get called once per paper
            logger.error(
                f"Multiple primary categories for {self.paper_id}: {self.primary} and {cat}"
            )
            self.add_cross(cat)  # add as a cross just to keep data
        else:
            catgory = CATEGORIES[cat]
            canon = catgory.get_canonical()
            self.primary = canon
            self.crosses.discard(
                canon
            )  # removes from crosses if present, the same category cant be both primary and cross.
            # This is relevant because an alternate name may be listed as a cross list

    def add_cross(self, cat: str):
        catgory = CATEGORIES[cat]
        canon = catgory.get_canonical()
        # avoid dupliciates of categories with other names
        if self.primary is None or canon != self.primary:
            self.crosses.add(canon)

    def __eq__(self, other):
        if not isinstance(other, PaperCategories):
            return False
        return (
            self.paper_id == other.paper_id
            and self.primary == other.primary
            and self.crosses == other.crosses
        )

    def __repr__(self):
        crosses_str = ", ".join(cat.id for cat in self.crosses)
        return (
            f"Paper: {self.paper_id} Primary: {self.primary.id} Crosses: {crosses_str}"
        )


class DownloadData:
    def __init__(
        self,
        paper_id: str,
        country: str,
        download_type: DOWNLOAD_TYPE,
        time: datetime,
        num: int,
    ):
        self.paper_id = paper_id
        self.country = country
        self.download_type = download_type
        self.time = time
        self.num = num

    def __repr__(self) -> str:
        return (
            f"DownloadData(paper_id='{self.paper_id}', country='{self.country}', "
            f"download_type='{self.download_type}', time='{self.time}', "
            f"num={self.num})"
        )


class DownloadCounts:
    def __init__(self, primary: int = 0, cross: int = 0):
        self.primary = primary
        self.cross = cross

    def __eq__(self, other):
        if isinstance(other, DownloadCounts):
            return self.primary == other.primary and self.cross == other.cross
        else:
            return False

    def __repr__(self):
        return f"Count(primary: {self.primary}, cross: {self.cross})"


class DownloadKey:
    def __init__(
        self,
        time: datetime,
        country: str,
        download_type: DOWNLOAD_TYPE,
        archive: str,
        category_id: str,
    ):
        self.time = time
        self.country = country
        self.download_type = download_type
        self.archive = archive
        self.category = category_id

    def __eq__(self, other):
        if isinstance(other, DownloadKey):
            return (
                self.country == other.country
                and self.download_type == other.download_type
                and self.category == other.category
                and self.time.date() == other.time.date()
                and self.time.hour == other.time.hour
            )
        return False

    def __hash__(self):
        return hash(
            (
                self.time.date(),
                self.time.hour,
                self.country,
                self.download_type,
                self.category,
            )
        )

    def __repr__(self):
        return f"Key(type: {self.download_type}, cat: {self.category}, country: {self.country}, day: {self.time.day} hour: {self.time.hour})"


class AggregationResult:
    def __init__(
        self,
        time_period_str: str,
        output_count: int,
        fetched_count: int,
        unique_ids_count: int,
        bad_id_count: int,
        problem_row_count: int,
    ):
        self.time_period_str = time_period_str
        self.output_count = output_count
        self.fetched_count = fetched_count
        self.unique_ids_count = unique_ids_count
        self.bad_id_count = bad_id_count
        self.problem_row_count = problem_row_count

    def single_run_str(self) -> str:
        return f"{self.time_period_str}: SUCCESS! rows created: {self.output_count}, fetched rows: {self.fetched_count}, unique_ids: {self.unique_ids_count}, invalid_ids: {self.bad_id_count}, other unprocessable rows: {self.problem_row_count}"

    def table_row_str(self) -> str:
        return f"{self.time_period_str:<20} {self.output_count:<7} {self.fetched_count:<12} {self.unique_ids_count:<10} {self.bad_id_count:<7} {self.problem_row_count:<10}"

    def table_header() -> str:
        return f"{'Time Period':<20} {'New Rows':<7} {'Fetched Rows':<12} {'Unique IDs':<10} {'Bad IDs':<7} {'Problems':<10} {'Time Taken':<10}"