import streamlit as st

st.title("Data & Methodology Improvements")

st.markdown("""
This page outlines potential improvements to enhance the accuracy and comprehensiveness of Truro's GHG emissions tracking.
""")

st.markdown("---")

# Improvement 1: Time-varying electricity emission factors
st.subheader("1. Time-Varying Electricity Emission Factor")

st.markdown("""
**Current Approach:**
- We use a single electricity emission factor: **0.000239 tCO2e per kWh**
- This factor is based on the current Massachusetts grid mix (fossil fuels, nuclear, renewables)
- Applied uniformly across all years (2019-2023)

**The Problem:**
- The grid is getting cleaner over time as renewable energy sources (solar, wind, offshore wind) increase
- Using a constant factor may overestimate current emissions and underestimate progress
- Massachusetts has been actively decarbonizing its grid, especially post-2020

**Proposed Improvement:**
- Obtain **annual electricity emission factors** for the Massachusetts grid
- Sources:
  - [EPA eGRID](https://www.epa.gov/egrid) - Regional electricity emission factors by year
  - [ISO New England](https://www.iso-ne.com/) - Real-time grid composition data
  - Massachusetts DOER reports
- Apply the appropriate factor for each year when calculating electricity emissions

**Expected Impact:**
- More accurate representation of emissions reductions from grid decarbonization
- Better separation of Truro's actions (heat pump adoption) from regional progress (cleaner grid)
- May show that recent electricity increases have lower climate impact than earlier years
""")

st.markdown("---")

# Improvement 2: Cross-reference assessors database
st.subheader("2. Cross-Reference Assessors Database with CLC Data")

st.markdown("""
**Current Approach:**
- Heat pump adoption tracked through Cape Light Compact program data
- Assume all heat pumps replace propane heating systems
- No detailed information on which fuel types are actually being replaced
- No square footage data to refine heating consumption estimates

**The Problem:**
- We don't know if heat pumps replaced propane, oil, electric resistance, or other systems
- Baseline heating consumption estimates use averages, not actual building sizes
- Can't validate the accuracy of our propane displacement calculations
- May be over- or under-estimating emissions reductions

**Proposed Improvement:**
- Obtain **updated assessors database** (more recent than 2019)
- Cross-reference CLC heat pump installation addresses with assessors property records
- For each heat pump installation, identify:
  - **Previous heating fuel type** (propane, oil, electric resistance, etc.)
  - **Building square footage** for more accurate consumption estimates
  - **Property type** (residential, commercial, seasonal)
  - **Installation timing** to better track year-over-year changes

**Expected Impact:**
- More accurate calculation of which fuel emissions are actually being reduced
- Better understanding of heat pump program effectiveness
- Refined heating consumption models based on actual building sizes
- Validation of current assumptions about propane displacement
- Could reveal if some conversions are from oil or electric rather than propane
""")

st.markdown("---")

# Improvement 3: Verify no double counting
st.subheader("3. Verify No Double Counting Between Categories")

st.markdown("""
**Current Categories:**
- **Municipal Buildings**: Town-owned building energy consumption
- **Vehicles**: Registered vehicles in Truro (includes town fleet + private vehicles)
- **Residential Energy**: Private home heating and electricity
- **Commercial Energy**: Business electricity consumption

**Potential Double Counting Concerns:**

**A. Electric Vehicle Home Charging** ✅ **ADDRESSED (with limitations)**
- Battery Electric vehicles charged at home are counted in residential electricity (Mass Save data)
- Including them in vehicle emissions would double count
- **Current Fix:**
  - Battery Electric vehicles: **Excluded** from vehicle totals (100% counted in residential electricity)
  - Plug-in Hybrid vehicles: Emissions **reduced by 50%** (assume half from home charging, half from gasoline)
  - Hybrid Electric vehicles: **100%** kept in vehicle total (self-charging, no home electricity)
- **Limitations:**
  - Assumes most EV charging occurs in Truro (at home)
  - Charging outside of town (workplace, public chargers elsewhere) would not be captured in residential electricity
  - May slightly undercount vehicle emissions if significant charging occurs outside Truro
  - May slightly overcount residential electricity if charging is primarily done outside Truro
  - **However**: Given current low EV adoption rates in Truro, this adjustment has minimal impact on total emissions

**B. Municipal Vehicles in Vehicle Count**
- The MassDOT vehicle census includes **all registered vehicles** in Truro
- This includes the town's municipal fleet
- Municipal fleet energy may already be tracked in municipal operations data

**C. Municipal Buildings in Electricity Data**
- Mass Save data may include municipal building electricity
- Need to verify if municipal consumption is separated from residential/commercial totals

**Proposed Verification:**
- **For Vehicles:**
  - ✅ Electric vehicle home charging addressed (see above)
  - Determine if municipal fleet is separately tracked in energy data
  - If yes, subtract municipal fleet from total vehicle emissions OR remove from municipal energy
  - Cross-reference with town fleet records

- **For Electricity:**
  - Contact Mass Save or Cape Light Compact to clarify data categorization
  - Verify whether municipal accounts are included in sector totals
  - Request breakdown that separates municipal from residential/commercial

**Expected Impact:**
- Ensure emissions totals are accurate and not inflated
- Proper attribution of emissions to municipal operations vs. community-wide
- More reliable baseline for tracking progress
- May reduce total emissions if double counting is occurring
""")

st.markdown("---")

# Summary and next steps
st.subheader("Implementation Priority")

st.markdown("""
**Recommended Order:**

1. **Immediate**: Verify double counting (Improvement #3)
   - Low effort, high impact on data accuracy
   - Can be done with existing contacts at Cape Light Compact and town records

2. **Short-term**: Time-varying electricity factors (Improvement #1)
   - Moderate effort, readily available data
   - EPA eGRID publishes annual factors
   - Would improve all electricity-related calculations

3. **Long-term**: Cross-reference assessors database (Improvement #2)
   - Higher effort, requires data access and analysis
   - Most comprehensive improvement
   - Would validate and refine multiple assumptions

These improvements would significantly enhance the accuracy and defensibility of Truro's emissions inventory.
""")
