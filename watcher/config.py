from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    name: str
    employer: str
    kind: str
    token: str
    query: str = ""

    @property
    def url(self) -> str:
        if self.kind == "greenhouse":
            return f"https://boards-api.greenhouse.io/v1/boards/{self.token}/jobs?content=true"
        if self.kind == "lever":
            return f"https://api.lever.co/v0/postings/{self.token}?mode=json"
        if self.kind == "smartrecruiters":
            query = "limit=100&offset=0&destination=PUBLIC"
            if self.query:
                query += f"&q={self.query}"
            return f"https://api.smartrecruiters.com/v1/companies/{self.token}/postings?{query}"
        raise ValueError(f"Unknown ATS kind: {self.kind}")


# These are public, no-login ATS boards. The list intentionally includes CRE
# brokerage, investment, development, property management, data-center, and
# commercial lending employers so the watchlist resembles the analyst market.
SOURCES = (
    Source("crexi", "Crexi", "greenhouse", "crexi"),
    Source("northmarq", "Northmarq", "greenhouse", "northmarq"),
    Source("sands_investment_group", "Sands Investment Group", "greenhouse", "sandsinvestmentgroup"),
    Source("flexential", "Flexential", "greenhouse", "flexentialcorp"),
    Source("centennial", "Centennial Real Estate Company", "greenhouse", "centennial"),
    Source("pma", "Property Management Associates", "greenhouse", "propertymanagementassociates"),
    Source("tpg", "TPG", "greenhouse", "tpgcareers"),
    Source("pretium", "Pretium", "greenhouse", "pretiumpartnersllc"),
    Source("rebuilt", "Rebuilt", "greenhouse", "rebuilt"),
    Source("nai_norcal", "NAI Northern California", "lever", "nainnorcal"),
    Source("beedie", "Beedie", "lever", "beedie"),
    Source("flow", "Flow", "lever", "flowlife"),
    Source("eq_bank", "EQ Bank", "lever", "eqbank"),
    Source("colliers", "Colliers", "smartrecruiters", "Colliers"),
    Source("turner_townsend", "Turner & Townsend", "smartrecruiters", "TurnerTownsend"),
    Source("svn_lord_partners", "SVN Lord Partners", "smartrecruiters", "SVNLordPartners"),
)

SOURCE_BY_NAME = {source.name: source for source in SOURCES}
