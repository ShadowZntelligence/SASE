#include "SemanticTrace.h"
#include <vector>
#include <cmath>

using namespace klee;

int TraceUtil::lcs(
    const SemanticTrace& A,
    const SemanticTrace& B)
{
    size_t n=A.tags.size();
    size_t m=B.tags.size();

    std::vector<std::vector<int>> dp(
        n+1,
        std::vector<int>(m+1,0));

    for(size_t i=1;i<=n;i++)
    {
        for(size_t j=1;j<=m;j++)
        {
            if(A.tags[i-1]==B.tags[j-1])
            {
                dp[i][j]=dp[i-1][j-1]+1;
            }
            else
            {
                dp[i][j]=std::max(
                    dp[i-1][j],
                    dp[i][j-1]);
            }
        }
    }

    return dp[n][m];
}

double TraceUtil::similarity(
    const SemanticTrace& st,
    const std::vector<GuidanceTrace>& guides)
{
    double score=0.0;

    for(auto &g : guides)
    {
        double w=std::pow(2.0,-g.rank);

        score+=
            w*
            lcs(st,g.trace);
    }

    return score;
}