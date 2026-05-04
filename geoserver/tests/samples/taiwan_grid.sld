<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0"
  xsi:schemaLocation="http://www.opengis.net/sld StyledLayerDescriptor.xsd"
  xmlns="http://www.opengis.net/sld"
  xmlns:ogc="http://www.opengis.net/ogc"
  xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <NamedLayer>
    <Name>taiwan_grid</Name>
    <UserStyle>
      <Name>taiwan_grid</Name>
      <FeatureTypeStyle>
        <Rule>
          <Name>NW - 北西（藍）</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>region</ogc:PropertyName>
              <ogc:Literal>NW</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#3498db</CssParameter>
              <CssParameter name="fill-opacity">0.65</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1a252f</CssParameter>
              <CssParameter name="stroke-width">2.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Name>NE - 北東（紅）</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>region</ogc:PropertyName>
              <ogc:Literal>NE</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#e74c3c</CssParameter>
              <CssParameter name="fill-opacity">0.65</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1a252f</CssParameter>
              <CssParameter name="stroke-width">2.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Name>SW - 西南（綠）</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>region</ogc:PropertyName>
              <ogc:Literal>SW</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#2ecc71</CssParameter>
              <CssParameter name="fill-opacity">0.65</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1a252f</CssParameter>
              <CssParameter name="stroke-width">2.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
        <Rule>
          <Name>SE - 東南（橙）</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>region</ogc:PropertyName>
              <ogc:Literal>SE</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PolygonSymbolizer>
            <Fill>
              <CssParameter name="fill">#f39c12</CssParameter>
              <CssParameter name="fill-opacity">0.65</CssParameter>
            </Fill>
            <Stroke>
              <CssParameter name="stroke">#1a252f</CssParameter>
              <CssParameter name="stroke-width">2.5</CssParameter>
            </Stroke>
          </PolygonSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
