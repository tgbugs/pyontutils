var github_xml = "https://raw.githubusercontent.com/SciCrunch/NIF-Ontology/xml-final";
function resolve_fragment() {
    if (window.location.hash) {
	var fragment = window.location.hash.substring(1);
	window.location.assign(window.location.pathname + "/" + fragment);
        console.log("Fragment detected, redirecting.");
        console.log(fragment);
    } else if (window.location.pathname.indexOf(".owl") > -1) {
	// we do this because we cannot redirect to github without
	// first checking whether the actual url had a fragment
	window.location.assign(window.location.pathname.replace("/NIF", github_xml));
    } else {
        console.log("Not an ontology file.");
    }
}
resolve_fragment();
