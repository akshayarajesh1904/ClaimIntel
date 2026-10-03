function showEditProfile() {

    document.getElementById("edit-profile").style.display = "block";

}


function saveProfile(event) {

    event.preventDefault();

    document.getElementById("save-message").style.display = "block";

}


function filterClaims() {

    let search = document.getElementById("claimSearch").value
        .toLowerCase()
        .trim();

    let status = document.getElementById("statusFilter").value
        .toLowerCase()
        .trim();

    let risk = document.getElementById("riskFilter").value
        .toLowerCase()
        .trim();

    let rows = document.querySelectorAll("#claimsTable tr");

    let found = 0;


    rows.forEach(function(row) {

        let claimId = row.querySelector(".claim-id")
            .textContent
            .toLowerCase()
            .trim();

        let claimStatus = row.querySelector(".claim-status")
            .textContent
            .toLowerCase()
            .trim();

        let claimRisk = row.querySelector(".risk")
            .textContent
            .toLowerCase()
            .trim();


        let matchesSearch =
            claimId.includes(search);


        let matchesStatus =
            status === "all" ||
            claimStatus === status;


        let matchesRisk =
            risk === "all" ||
            claimRisk === risk;


        if (
            matchesSearch &&
            matchesStatus &&
            matchesRisk
        ) {

            row.style.display = "";

            found++;

        } else {

            row.style.display = "none";

        }

    });


    if (found === 0) {

        document.getElementById("noResults").style.display = "block";

    } else {

        document.getElementById("noResults").style.display = "none";

    }

}

function approveClaim() {

    let message = document.getElementById("decision-message");

    message.textContent = "✓ Claim approved successfully.";

    message.style.display = "block";

    message.style.background = "#d4edda";

    message.style.color = "#155724";

    setTimeout(function() {

        window.location.href = "officer-pending.html";

    }, 1500);

}


function investigateClaim() {

    let message = document.getElementById("decision-message");

    message.textContent = "⚠ Investigation has been requested.";

    message.style.display = "block";

    message.style.background = "#fff3cd";

    message.style.color = "#856404";

    setTimeout(function() {

        window.location.href = "officer-pending.html";

    }, 1500);

}


function rejectClaim() {

    let message = document.getElementById("decision-message");

    message.textContent = "✕ Claim rejected.";

    message.style.display = "block";

    message.style.background = "#f8d7da";

    message.style.color = "#721c24";

    setTimeout(function() {

        window.location.href = "officer-pending.html";

    }, 1500);

}

function viewDocument(documentName) {

    alert(
        "Opening " + documentName + "..."
    );

}


function downloadDocument(documentName) {

    alert(
        "Downloading " + documentName + "..."
    );

}
function searchUsers() {

    let input = document.getElementById("userSearch");

    let filter = input.value.toLowerCase();

    let table = document.getElementById("usersTable");

    let rows = table.getElementsByTagName("tbody")[0].getElementsByTagName("tr");


    for (let i = 0; i < rows.length; i++) {

        let userId = rows[i].cells[0].textContent.toLowerCase();

        let email = rows[i].cells[2].textContent.toLowerCase();


        if (
            userId.includes(filter) ||
            email.includes(filter)
        ) {

            rows[i].style.display = "";

        } else {

            rows[i].style.display = "none";

        }

    }

}

function searchOfficers() {

    let input = document.getElementById("officerSearch");

    let filter = input.value.toLowerCase();

    let table = document.getElementById("officersTable");

    let rows = table.getElementsByTagName("tbody")[0].getElementsByTagName("tr");


    for (let i = 0; i < rows.length; i++) {

        let officerId = rows[i].cells[0].textContent.toLowerCase();

        let email = rows[i].cells[2].textContent.toLowerCase();


        if (
            officerId.includes(filter) ||
            email.includes(filter)
        ) {

            rows[i].style.display = "";

        } else {

            rows[i].style.display = "none";

        }

    }

}

function searchAdminClaims() {

    let input = document.getElementById("adminClaimSearch");

    let filter = input.value.toLowerCase();

    let table = document.getElementById("adminClaimsTable");

    let rows = table
        .getElementsByTagName("tbody")[0]
        .getElementsByTagName("tr");


    for (let i = 0; i < rows.length; i++) {

        let claimId = rows[i].cells[0].textContent.toLowerCase();

        let policyholderId = rows[i].cells[1].textContent.toLowerCase();


        if (
            claimId.includes(filter) ||
            policyholderId.includes(filter)
        ) {

            rows[i].style.display = "";

        } else {

            rows[i].style.display = "none";

        }

    }

}